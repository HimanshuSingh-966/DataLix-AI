"""Ingestion Agent — loads the cached DataFrame and builds the schema.

Responsibilities:
1. Load the cached DataFrame for the given session_id
2. Build a rich schema dict (dtype, null info, unique counts, sample values)
3. Handle edge cases (all-null cols, single-row datasets, ID columns, mixed types)
"""

import logging
import sys
import os
import numpy as np

# Allow imports from parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_processor import get_cached_df

logger = logging.getLogger("datalix.agents.ingestion")


def _classify_dtype(series) -> str:
    """Classify a pandas Series into a human-readable type."""
    import pandas as pd
    dtype = series.dtype

    if pd.api.types.is_bool_dtype(dtype):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "datetime"
    if pd.api.types.is_numeric_dtype(dtype):
        return "numeric"
    # Check if object column looks like datetime
    if dtype == object:
        non_null = series.dropna()
        if len(non_null) > 0:
            sample = non_null.head(20)
            try:
                pd.to_datetime(sample, format="mixed")
                return "datetime_string"
            except (ValueError, TypeError):
                pass
    return "categorical"


def ingestion_node(state: dict) -> dict:
    """Load cached DataFrame and build schema.

    Args:
        state: DataLixState dict with at least 'session_id' set.

    Returns:
        Updated state with raw_df, schema, current_agent set.
    """
    import pandas as pd

    session_id = state["session_id"]
    logger.info(f"Ingestion agent starting for session {session_id[:8]}")

    # 1. Load from cache
    df = get_cached_df(session_id)
    if df is None:
        state["error"] = "Dataset not found. Please re-upload."
        state["current_agent"] = "ingestion_error"
        logger.error(f"No cached DataFrame for session {session_id[:8]}")
        return state

    state["raw_df"] = df

    # 2. Build schema
    schema = {}
    for col in df.columns:
        series = df[col]
        null_count = int(series.isnull().sum())
        null_pct = round((null_count / len(df)) * 100, 2) if len(df) > 0 else 0.0
        unique_count = int(series.nunique())
        dtype_class = _classify_dtype(series)

        col_schema = {
            "dtype": dtype_class,
            "pandas_dtype": str(series.dtype),
            "null_count": null_count,
            "null_pct": null_pct,
            "unique_count": unique_count,
            "total_rows": len(df),
        }

        # Sample values (first 3 non-null)
        non_null = series.dropna()
        if len(non_null) > 0:
            samples = non_null.head(3).tolist()
            # Convert numpy types to Python natives for JSON safety
            col_schema["sample_values"] = [
                float(v) if isinstance(v, (np.integer, np.floating)) else str(v)
                for v in samples
            ]
        else:
            col_schema["sample_values"] = []

        # Numeric extras
        if dtype_class == "numeric" and len(non_null) > 0:
            col_schema["min"] = float(non_null.min())
            col_schema["max"] = float(non_null.max())
            col_schema["mean"] = float(non_null.mean())
            col_schema["median"] = float(non_null.median())

        # Flag potential ID columns (100% unique)
        if unique_count == len(df) and len(df) > 1:
            col_schema["likely_id"] = True

        # Flag all-null columns
        if null_count == len(df):
            col_schema["all_null"] = True

        # Flag mixed-type columns
        if series.dtype == object and len(non_null) > 0:
            types = non_null.apply(type).unique()
            if len(types) > 1:
                col_schema["mixed_types"] = True

        schema[col] = col_schema

    state["schema"] = schema
    state["current_agent"] = "ingestion_complete"

    logger.info(
        f"Ingestion complete: {len(df)} rows, {len(df.columns)} cols, "
        f"{sum(1 for s in schema.values() if s['null_count'] > 0)} cols with nulls"
    )
    return state
