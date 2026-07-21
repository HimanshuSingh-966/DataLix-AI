"""Diagnosis Agent — identifies data quality issues and scores them by severity.

Severity levels:
  CRITICAL  — blocks analysis  (−20 pts each)
  WARNING   — degrades quality  (−8 pts each)
  INFO      — informational     (−2 pts each)
"""

import logging
import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger("datalix.agents.diagnosis")


def _detect_outliers_iqr(series) -> int:
    """Count outliers using IQR method. Returns count."""
    clean = series.dropna()
    if len(clean) < 4:
        return 0
    Q1 = clean.quantile(0.25)
    Q3 = clean.quantile(0.75)
    IQR = Q3 - Q1
    if IQR == 0:
        return 0
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    return int(((clean < lower) | (clean > upper)).sum())


def diagnosis_node(state: dict) -> dict:
    """Analyze data quality and produce a scored report.

    Reads state["schema"] and state["raw_df"].
    Writes state["quality_report"].
    """
    import pandas as pd

    schema = state.get("schema", {})
    df = state.get("raw_df")

    if df is None:
        state["error"] = "No DataFrame available for diagnosis."
        state["current_agent"] = "diagnosis_error"
        return state

    logger.info(f"Diagnosis agent starting: {len(df)} rows, {len(schema)} cols")

    issues = []

    # ── Per-column checks ──────────────────────────────────────────
    for col, info in schema.items():
        null_pct = info.get("null_pct", 0)
        unique_count = info.get("unique_count", 0)
        dtype_class = info.get("dtype", "categorical")
        pandas_dtype = info.get("pandas_dtype", "")

        # CRITICAL: null_pct > 50%
        if null_pct > 50:
            issues.append({
                "column": col,
                "type": "critical_nulls",
                "severity": "critical",
                "description": f"{col} has {null_pct}% null values — over 50%, recommend dropping",
                "affected_rows": info.get("null_count", 0),
            })

        # CRITICAL: single unique value (constant column)
        if unique_count <= 1 and not info.get("all_null", False):
            issues.append({
                "column": col,
                "type": "constant_column",
                "severity": "critical",
                "description": f"{col} has only {unique_count} unique value — no variance",
                "affected_rows": len(df),
            })

        # CRITICAL: numeric stored as object dtype
        if dtype_class == "categorical" and pandas_dtype == "object":
            non_null = df[col].dropna()
            if len(non_null) > 0:
                numeric_count = pd.to_numeric(non_null, errors="coerce").notna().sum()
                if numeric_count > len(non_null) * 0.8:
                    issues.append({
                        "column": col,
                        "type": "numeric_as_string",
                        "severity": "critical",
                        "description": f"{col} looks numeric but stored as text ({numeric_count}/{len(non_null)} parseable)",
                        "affected_rows": int(len(non_null)),
                    })

        # WARNING: null_pct between 20-50%
        if 20 <= null_pct <= 50:
            issues.append({
                "column": col,
                "type": "moderate_nulls",
                "severity": "warning",
                "description": f"{col} has {null_pct}% null values — needs imputation",
                "affected_rows": info.get("null_count", 0),
            })

        # WARNING: outliers (numeric only)
        if dtype_class == "numeric":
            outlier_count = _detect_outliers_iqr(df[col])
            if outlier_count > 0:
                issues.append({
                    "column": col,
                    "type": "outliers",
                    "severity": "warning",
                    "description": f"{outlier_count} outliers detected in {col} (IQR method)",
                    "affected_rows": outlier_count,
                })

        # INFO: null_pct between 5-20%
        if 5 <= null_pct < 20:
            issues.append({
                "column": col,
                "type": "minor_nulls",
                "severity": "info",
                "description": f"{col} has {null_pct}% null values — minor, can be imputed",
                "affected_rows": info.get("null_count", 0),
            })

        # INFO: high cardinality categorical (>50 unique values)
        if dtype_class == "categorical" and unique_count > 50:
            issues.append({
                "column": col,
                "type": "high_cardinality",
                "severity": "info",
                "description": f"{col} has {unique_count} unique values — high cardinality categorical",
                "affected_rows": 0,
            })

        # INFO: potential datetime stored as string
        if dtype_class == "datetime_string":
            issues.append({
                "column": col,
                "type": "datetime_as_string",
                "severity": "info",
                "description": f"{col} looks like datetime but stored as string",
                "affected_rows": 0,
            })

    # ── Dataset-level checks ───────────────────────────────────────

    # WARNING: duplicate rows
    dup_count = int(df.duplicated().sum())
    if dup_count > 0:
        issues.append({
            "column": "__dataset__",
            "type": "duplicates",
            "severity": "warning",
            "description": f"Found {dup_count} duplicate rows ({round(dup_count / len(df) * 100, 1)}%)",
            "affected_rows": dup_count,
        })

    # ── Scoring ────────────────────────────────────────────────────
    critical_count = sum(1 for i in issues if i["severity"] == "critical")
    warning_count = sum(1 for i in issues if i["severity"] == "warning")
    info_count = sum(1 for i in issues if i["severity"] == "info")

    score = 100
    score -= critical_count * 20
    score -= warning_count * 8
    score -= info_count * 2
    score = max(0, score)

    quality_report = {
        "overall_score": score,
        "issue_count": {
            "critical": critical_count,
            "warning": warning_count,
            "info": info_count,
        },
        "issues": issues,
    }

    state["quality_report"] = quality_report
    state["current_agent"] = "diagnosis_complete"

    logger.info(
        f"Diagnosis complete: score={score}, "
        f"critical={critical_count}, warning={warning_count}, info={info_count}"
    )
    return state
