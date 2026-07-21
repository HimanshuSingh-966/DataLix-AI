import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from sklearn.impute import KNNImputer

MAX_KNN_ROWS = 50000
MAX_KNN_COLUMNS = 50

def clean_dataset(df: pd.DataFrame, parameters: Dict) -> Dict[str, Any]:
    """
    Clean dataset based on parameters
    Supports: missing values, outliers, duplicates, normalization
    """
    
    df_clean = df.copy()
    changes = []
    
    # Handle missing values
    if parameters.get('handleMissing'):
        method = parameters.get('missingMethod', 'drop')
        columns = parameters.get('missingColumns', df.columns.tolist())
        
        result = handle_missing_values(df_clean, columns, method, parameters)
        df_clean = result['dataframe']
        changes.append(result['message'])
    
    # Handle duplicates
    if parameters.get('removeDuplicates'):
        before = len(df_clean)
        subset = parameters.get('duplicateSubset')
        keep = parameters.get('duplicateKeep', 'first')
        
        df_clean = df_clean.drop_duplicates(subset=subset, keep=keep)
        removed = before - len(df_clean)
        
        if removed > 0:
            changes.append(f"Removed {removed} duplicate rows")
    
    # Handle outliers
    if parameters.get('handleOutliers'):
        method = parameters.get('outlierMethod', 'iqr')
        columns = parameters.get('outlierColumns', df_clean.select_dtypes(include=[np.number]).columns.tolist())
        
        result = detect_and_handle_outliers(df_clean, columns, method, parameters)
        df_clean = result['dataframe']
        changes.append(result['message'])
    
    # Normalize/standardize
    if parameters.get('normalize'):
        method = parameters.get('normalizeMethod', 'minmax')
        columns = parameters.get('normalizeColumns', df_clean.select_dtypes(include=[np.number]).columns.tolist())
        
        result = normalize_data(df_clean, columns, method)
        df_clean = result['dataframe']
        changes.append(result['message'])
    
    message = f"Data cleaned successfully. Changes: {'; '.join(changes)}" if changes else "No changes made"
    
    return {
        "dataframe": df_clean,
        "message": message,
        "changes": changes,
        "rowsBefore": len(df),
        "rowsAfter": len(df_clean)
    }

def handle_missing_values(
    df: pd.DataFrame, 
    columns: List[str], 
    method: str,
    parameters: Dict
) -> Dict[str, Any]:
    """Handle missing values using various methods"""
    
    df_result = df.copy()
    total_missing_before = df[columns].isnull().sum().sum()
    
    if method == 'drop':
        df_result = df_result.dropna(subset=columns)
        message = f"Dropped rows with missing values in {len(columns)} columns"
    
    elif method == 'mean':
        for col in columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                df_result.loc[:, col] = df_result[col].fillna(df[col].mean())
        message = f"Filled missing values with mean in {len(columns)} numeric columns"
    
    elif method == 'median':
        for col in columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                df_result.loc[:, col] = df_result[col].fillna(df[col].median())
        message = f"Filled missing values with median in {len(columns)} numeric columns"
    
    elif method == 'mode':
        for col in columns:
            mode_val = df[col].mode()
            if len(mode_val) > 0:
                df_result.loc[:, col] = df_result[col].fillna(mode_val[0])
        message = f"Filled missing values with mode in {len(columns)} columns"
    
    elif method == 'forward_fill':
        df_result.loc[:, columns] = df_result[columns].ffill()
        message = f"Forward filled missing values in {len(columns)} columns"
    
    elif method == 'backward_fill':
        df_result.loc[:, columns] = df_result[columns].bfill()
        message = f"Backward filled missing values in {len(columns)} columns"
    
    elif method == 'knn':
        numeric_cols = [col for col in columns if pd.api.types.is_numeric_dtype(df[col])]
        if numeric_cols:
            if len(df) > MAX_KNN_ROWS:
                message = f"KNN imputation skipped: dataset too large ({len(df)} rows, max {MAX_KNN_ROWS}). Use mean/median/interpolation instead."
            elif len(numeric_cols) > MAX_KNN_COLUMNS:
                message = f"KNN imputation skipped: too many numeric columns ({len(numeric_cols)}, max {MAX_KNN_COLUMNS}). Select fewer columns."
            else:
                k_neighbors = parameters.get('knnNeighbors', 5)
                imputer = KNNImputer(n_neighbors=k_neighbors)
                df_result[numeric_cols] = imputer.fit_transform(df[numeric_cols])
                message = f"KNN imputed missing values in {len(numeric_cols)} numeric columns (k={k_neighbors})"
        else:
            message = "No numeric columns found for KNN imputation"
    
    elif method == 'interpolation':
        for col in columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                df_result[col] = df_result[col].interpolate()
        message = f"Interpolated missing values in {len(columns)} numeric columns"
    
    else:
        raise ValueError(f"Unsupported imputation method: {method}")
    
    total_missing_after = df_result[columns].isnull().sum().sum()
    imputed = total_missing_before - total_missing_after
    
    return {
        "dataframe": df_result,
        "message": message,
        "missingBefore": int(total_missing_before),
        "missingAfter": int(total_missing_after),
        "imputed": int(imputed)
    }

def detect_and_handle_outliers(
    df: pd.DataFrame,
    columns: List[str],
    method: str,
    parameters: Dict
) -> Dict[str, Any]:
    """Detect and handle outliers"""
    
    df_result = df.copy()
    rows_before = len(df)
    outliers_found = 0
    
    action = parameters.get('outlierAction', 'remove')  # remove, cap, flag
    
    for col in columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        
        series = df_result[col].dropna()
        
        if method == 'iqr':
            threshold = parameters.get('iqrThreshold', 1.5)
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR
            
            outlier_mask = (df_result[col] < lower_bound) | (df_result[col] > upper_bound)
        
        elif method == 'zscore':
            threshold = parameters.get('zscoreThreshold', 3)
            z_scores = np.abs((df_result[col] - series.mean()) / series.std())
            outlier_mask = z_scores > threshold
        
        else:
            raise ValueError(f"Unsupported outlier detection method: {method}")
        
        outliers_count = outlier_mask.sum()
        outliers_found += outliers_count
        
        if action == 'remove':
            df_result = df_result[~outlier_mask]
        elif action == 'cap':
            if method == 'iqr':
                df_result.loc[df_result[col] < lower_bound, col] = lower_bound
                df_result.loc[df_result[col] > upper_bound, col] = upper_bound
        elif action == 'flag':
            df_result[f'{col}_outlier'] = outlier_mask
    
    rows_after = len(df_result)
    removed = rows_before - rows_after
    
    message = f"Detected {outliers_found} outliers using {method} method. "
    if action == 'remove':
        message += f"Removed {removed} rows."
    elif action == 'cap':
        message += "Capped outliers to boundaries."
    elif action == 'flag':
        message += "Flagged outliers in new columns."
    
    return {
        "dataframe": df_result,
        "message": message,
        "outliersDetected": int(outliers_found),
        "rowsRemoved": int(removed)
    }

def remove_duplicates(df: pd.DataFrame, subset: Optional[List[str]] = None, keep: str = 'first') -> Dict[str, Any]:
    """Remove duplicate rows"""
    
    rows_before = len(df)
    df_result = df.drop_duplicates(subset=subset, keep=keep)
    rows_after = len(df_result)
    removed = rows_before - rows_after
    
    return {
        "dataframe": df_result,
        "rowsRemoved": int(removed),
        "rowsBefore": int(rows_before),
        "rowsAfter": int(rows_after),
        "percentage": float((removed / rows_before) * 100) if rows_before > 0 else 0
    }

def normalize_data(df: pd.DataFrame, columns: List[str], method: str = 'minmax') -> Dict[str, Any]:
    """Normalize numeric data"""
    
    df_result = df.copy()
    
    for col in columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        
        if method == 'minmax':
            # Min-max normalization to [0, 1]
            min_val = df[col].min()
            max_val = df[col].max()
            if max_val != min_val:
                df_result[col] = (df[col] - min_val) / (max_val - min_val)
        
        elif method == 'zscore':
            # Z-score standardization
            mean_val = df[col].mean()
            std_val = df[col].std()
            if std_val != 0:
                df_result[col] = (df[col] - mean_val) / std_val
        
        elif method == 'robust':
            # Robust scaling using median and IQR
            median_val = df[col].median()
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            if IQR != 0:
                df_result[col] = (df[col] - median_val) / IQR
    
    return {
        "dataframe": df_result,
        "message": f"Normalized {len(columns)} columns using {method} method"
    }
