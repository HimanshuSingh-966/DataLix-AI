import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any

def calculate_statistics(df: pd.DataFrame, columns: Optional[List[str]] = None) -> Dict[str, Any]:
    """Calculate comprehensive statistical summary"""
    
    # Select numeric columns
    if columns:
        numeric_cols = [col for col in columns if col in df.columns and pd.api.types.is_numeric_dtype(df[col])]
    else:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if not numeric_cols:
        return {"statistics": [], "summary": "No numeric columns found"}
    
    stats_list = []
    
    for col in numeric_cols:
        series = df[col].dropna()
        
        if len(series) == 0:
            continue
        
        stats_list.append({
            "column": col,
            "mean": float(series.mean()),
            "median": float(series.median()),
            "std": float(series.std()),
            "min": float(series.min()),
            "max": float(series.max()),
            "count": int(series.count()),
            "q25": float(series.quantile(0.25)),
            "q75": float(series.quantile(0.75))
        })
    
    return {
        "statistics": stats_list,
        "numericColumns": numeric_cols,
        "totalColumns": len(df.columns)
    }

def calculate_correlation(df: pd.DataFrame, columns: Optional[List[str]] = None) -> Dict[str, Any]:
    """Calculate correlation matrix"""
    
    # Select numeric columns
    if columns:
        numeric_cols = [col for col in columns if col in df.columns and pd.api.types.is_numeric_dtype(df[col])]
    else:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if len(numeric_cols) < 2:
        return {"error": "Need at least 2 numeric columns for correlation"}
    
    # Calculate correlation matrix
    corr_df = df[numeric_cols].corr()
    
    # Convert to list and handle NaN values
    matrix_values = corr_df.values.tolist()
    # Replace any NaN with None for JSON serialization
    clean_matrix = []
    for row in matrix_values:
        clean_row = []
        for val in row:
            if isinstance(val, (np.floating, float)) and np.isnan(val):
                clean_row.append(None)
            elif isinstance(val, (np.integer, np.floating)):
                clean_row.append(float(val))
            else:
                clean_row.append(val)
        clean_matrix.append(clean_row)
    
    return {
        "columns": numeric_cols,
        "matrix": clean_matrix
    }

def describe_distribution(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """Analyze distribution of a column"""
    
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found")
    
    series = df[column].dropna()
    
    if pd.api.types.is_numeric_dtype(series):
        # Numeric distribution
        return {
            "type": "numeric",
            "stats": {
                "mean": float(series.mean()),
                "median": float(series.median()),
                "std": float(series.std()),
                "skewness": float(series.skew()),
                "kurtosis": float(series.kurtosis()),
                "min": float(series.min()),
                "max": float(series.max())
            },
            "histogram": series.value_counts(bins=20, sort=False).to_dict()
        }
    else:
        # Categorical distribution
        value_counts = series.value_counts().head(20)
        return {
            "type": "categorical",
            "uniqueValues": int(series.nunique()),
            "valueCounts": value_counts.to_dict(),
            "topValues": value_counts.index.tolist()[:10]
        }
