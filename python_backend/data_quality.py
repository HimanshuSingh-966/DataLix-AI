import pandas as pd
import numpy as np
from typing import Dict, List, Any

def analyze_data_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Comprehensive data quality analysis
    Returns scores for completeness, consistency, uniqueness, validity
    """
    
    if df.empty:
        return {
            "overallScore": 0,
            "completeness": 0,
            "consistency": 0,
            "uniqueness": 0,
            "validity": 0,
            "columnMetrics": [],
            "issues": [],
            "recommendations": ["Upload a dataset to begin analysis"]
        }
    
    total_cells = df.shape[0] * df.shape[1]
    
    # Completeness: percentage of non-null values
    total_missing = df.isnull().sum().sum()
    completeness = 1 - (total_missing / total_cells) if total_cells > 0 else 0
    
    # Column-level metrics
    column_metrics = []
    for col in df.columns:
        null_count = df[col].isnull().sum()
        missing_pct = (null_count / len(df)) * 100 if len(df) > 0 else 0
        unique_count = df[col].nunique()
        non_null_values = df[col].dropna()
        
        # Get sample values and convert to native Python types
        if len(non_null_values) > 0:
            unique_vals = non_null_values.unique()[:3]
            sample_values = []
            for val in unique_vals:
                # Convert numpy types to Python native types
                if isinstance(val, (np.integer, np.floating)):
                    sample_values.append(float(val))
                elif isinstance(val, np.ndarray):
                    sample_values.append(val.tolist())
                else:
                    sample_values.append(str(val))
        else:
            sample_values = []
        
        column_metrics.append({
            "column": col,
            "missingPercentage": float(missing_pct),
            "uniqueValues": int(unique_count),
            "dataType": str(df[col].dtype),
            "sampleValues": sample_values
        })
    
    # Consistency: check for mixed data types within columns
    consistency_score = 1.0
    inconsistent_cols = []
    
    for col in df.columns:
        # For object columns, check if there's type mixing
        if df[col].dtype == 'object':
            non_null = df[col].dropna()
            if len(non_null) > 0:
                types = non_null.apply(type).unique()
                if len(types) > 1:
                    consistency_score -= 0.05
                    inconsistent_cols.append(col)
    
    consistency = max(0, min(1, consistency_score))
    
    # Uniqueness: percentage of unique rows
    duplicate_count = df.duplicated().sum()
    uniqueness = 1 - (duplicate_count / len(df)) if len(df) > 0 else 1
    
    # Validity: simplified - assume high validity, check for basic issues
    validity = 0.9
    
    # Overall score (weighted average)
    overall_score = (
        completeness * 0.4 +
        consistency * 0.3 +
        uniqueness * 0.2 +
        validity * 0.1
    )
    
    # Detect issues
    issues = []
    
    # High missing values
    high_missing = [m for m in column_metrics if m["missingPercentage"] > 20]
    if high_missing:
        issues.append({
            "type": "missing_values",
            "severity": "high",
            "count": len(high_missing),
            "description": f"{len(high_missing)} columns have >20% missing values: {', '.join([m['column'] for m in high_missing[:3]])}"
        })
    
    # Duplicates
    if duplicate_count > 0:
        severity = "high" if duplicate_count > len(df) * 0.1 else "medium"
        issues.append({
            "type": "duplicates",
            "severity": severity,
            "count": int(duplicate_count),
            "description": f"Found {duplicate_count} duplicate rows ({(duplicate_count/len(df)*100):.1f}%)"
        })
    
    # Inconsistent types
    if inconsistent_cols:
        issues.append({
            "type": "inconsistency",
            "severity": "medium",
            "count": len(inconsistent_cols),
            "description": f"{len(inconsistent_cols)} columns have mixed data types: {', '.join(inconsistent_cols[:3])}"
        })
    
    # Outlier detection for numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        outliers = detect_outliers_iqr(df[col].dropna())
        if len(outliers) > 0:
            issues.append({
                "type": "outliers",
                "severity": "low",
                "column": col,
                "count": len(outliers),
                "description": f"{len(outliers)} potential outliers in {col}"
            })
    
    # Recommendations
    recommendations = []
    
    if high_missing:
        recommendations.append(f"Handle missing values in: {', '.join([m['column'] for m in high_missing[:3]])}")
    
    if duplicate_count > 0:
        recommendations.append(f"Remove {duplicate_count} duplicate rows to improve data quality")
    
    if inconsistent_cols:
        recommendations.append(f"Standardize data types in: {', '.join(inconsistent_cols[:3])}")
    
    if not issues:
        recommendations.append("Your data quality is excellent! You can proceed with analysis.")
    
    return {
        "overallScore": int(overall_score * 100),
        "completeness": float(completeness),
        "consistency": float(consistency),
        "uniqueness": float(uniqueness),
        "validity": float(validity),
        "columnMetrics": column_metrics,
        "issues": issues,
        "recommendations": recommendations
    }

def detect_outliers_iqr(series: pd.Series) -> List:
    """Detect outliers using IQR method"""
    if len(series) < 4:
        return []
    
    Q1 = series.quantile(0.25)
    Q3 = series.quantile(0.75)
    IQR = Q3 - Q1
    
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    outliers = series[(series < lower_bound) | (series > upper_bound)]
    return outliers.tolist()
