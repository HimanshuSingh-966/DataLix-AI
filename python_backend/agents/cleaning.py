"""Cleaning Agent — fixes data quality issues from the diagnosis report.

Rules:
  1. NEVER mutate raw_df — always work on a copy in clean_df.
  2. EVERY modification writes to audit_log FIRST.
  3. Reversible actions are flagged for the Undo feature.
"""

import logging
import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger("datalix.agents.cleaning")


def _make_audit_entry(
    column: str,
    action: str,
    reason: str,
    rows_affected: int,
    reversible: bool = False,
    original_stats: dict = None,
    new_stats: dict = None,
) -> dict:
    """Create a standardized AuditEntry dict."""
    return {
        "column": column,
        "action": action,
        "reason": reason,
        "rows_affected": rows_affected,
        "reversible": reversible,
        "original_stats": original_stats or {},
        "new_stats": new_stats or {},
    }


def cleaning_node(state: dict) -> dict:
    """Fix issues from quality_report. Log every decision to audit_log.

    Reads: state["raw_df"], state["quality_report"]
    Writes: state["clean_df"], state["audit_log"]
    """
    import pandas as pd

    raw_df = state.get("raw_df")
    quality_report = state.get("quality_report", {})
    issues = quality_report.get("issues", [])

    if raw_df is None:
        state["error"] = "No DataFrame available for cleaning."
        state["current_agent"] = "cleaning_error"
        return state

    logger.info(f"Cleaning agent starting: {len(issues)} issues to address")

    # 1. Work on a copy — never mutate raw_df
    clean_df = raw_df.copy()
    audit_log = []

    # Group issues by type for efficient processing
    duplicates = [i for i in issues if i["type"] == "duplicates"]
    moderate_nulls = [i for i in issues if i["type"] == "moderate_nulls"]
    minor_nulls = [i for i in issues if i["type"] == "minor_nulls"]
    outlier_issues = [i for i in issues if i["type"] == "outliers"]
    constant_cols = [i for i in issues if i["type"] == "constant_column"]
    critical_nulls = [i for i in issues if i["type"] == "critical_nulls"]

    # ── DUPLICATES ──────────────────────────────────────────────────
    for issue in duplicates:
        dup_count = int(clean_df.duplicated().sum())
        if dup_count > 0:
            entry = _make_audit_entry(
                column="__dataset__",
                action="dropped_duplicates",
                reason=f"Removed {dup_count} exact duplicate rows",
                rows_affected=dup_count,
                reversible=False,
                original_stats={"row_count": len(clean_df)},
            )
            audit_log.append(entry)
            clean_df = clean_df.drop_duplicates().reset_index(drop=True)
            entry["new_stats"] = {"row_count": len(clean_df)}
            logger.info(f"Dropped {dup_count} duplicates")

    # ── NULLS IN NUMERIC (null_pct < 50%) ──────────────────────────
    null_issues = moderate_nulls + minor_nulls
    for issue in null_issues:
        col = issue["column"]
        if col not in clean_df.columns:
            continue

        null_count = int(clean_df[col].isnull().sum())
        if null_count == 0:
            continue

        schema_info = state.get("schema", {}).get(col, {})
        dtype_class = schema_info.get("dtype", "categorical")

        if dtype_class == "numeric":
            # Impute with median (robust to skew)
            median_val = float(clean_df[col].median())
            original_mean = float(clean_df[col].mean()) if clean_df[col].notna().any() else 0

            entry = _make_audit_entry(
                column=col,
                action="imputed_median",
                reason=f"Numeric column — filled {null_count} nulls with median ({median_val:.2f})",
                rows_affected=null_count,
                reversible=False,
                original_stats={"null_count": null_count, "mean": original_mean},
            )
            audit_log.append(entry)
            clean_df[col] = clean_df[col].fillna(median_val)
            entry["new_stats"] = {
                "null_count": int(clean_df[col].isnull().sum()),
                "mean": float(clean_df[col].mean()),
            }
            logger.info(f"Imputed median for {col}: {null_count} nulls filled")

        else:
            # Categorical — impute with mode
            mode_vals = clean_df[col].mode()
            if len(mode_vals) > 0:
                mode_val = mode_vals.iloc[0]
                entry = _make_audit_entry(
                    column=col,
                    action="imputed_mode",
                    reason=f"Categorical column — filled {null_count} nulls with mode ('{mode_val}')",
                    rows_affected=null_count,
                    reversible=False,
                    original_stats={"null_count": null_count},
                )
                audit_log.append(entry)
                clean_df[col] = clean_df[col].fillna(mode_val)
                entry["new_stats"] = {"null_count": int(clean_df[col].isnull().sum())}
                logger.info(f"Imputed mode for {col}: {null_count} nulls filled with '{mode_val}'")

    # ── OUTLIERS ────────────────────────────────────────────────────
    for issue in outlier_issues:
        col = issue["column"]
        if col not in clean_df.columns:
            continue
        if not pd.api.types.is_numeric_dtype(clean_df[col]):
            continue

        series = clean_df[col].dropna()
        if len(series) < 4:
            continue

        p5 = float(series.quantile(0.05))
        p95 = float(series.quantile(0.95))
        original_min = float(series.min())
        original_max = float(series.max())

        # Cap at 5th and 95th percentile
        capped = clean_df[col].clip(lower=p5, upper=p95)
        rows_affected = int((clean_df[col] != capped).sum())

        if rows_affected > 0:
            entry = _make_audit_entry(
                column=col,
                action="capped_outliers",
                reason=f"Capped {rows_affected} outlier values to [P5={p5:.2f}, P95={p95:.2f}]",
                rows_affected=rows_affected,
                reversible=False,
                original_stats={"min": original_min, "max": original_max},
                new_stats={"min": p5, "max": p95},
            )
            audit_log.append(entry)
            clean_df[col] = capped
            logger.info(f"Capped outliers in {col}: {rows_affected} values clipped")

    # ── USELESS COLUMNS (1 unique value) ───────────────────────────
    for issue in constant_cols:
        col = issue["column"]
        entry = _make_audit_entry(
            column=col,
            action="flagged_for_review",
            reason="Single unique value — possible constant. Consider dropping.",
            rows_affected=len(clean_df),
            reversible=True,
        )
        audit_log.append(entry)
        logger.info(f"Flagged constant column: {col}")

    # ── CRITICAL NULLS (null_pct > 50%) ────────────────────────────
    for issue in critical_nulls:
        col = issue["column"]
        null_pct = state.get("schema", {}).get(col, {}).get("null_pct", 0)
        entry = _make_audit_entry(
            column=col,
            action="flagged_for_review",
            reason=f"Over {null_pct}% null — recommend dropping this column.",
            rows_affected=issue.get("affected_rows", 0),
            reversible=True,
        )
        audit_log.append(entry)
        logger.info(f"Flagged critical nulls column: {col} ({null_pct}%)")

    # 3. Store results
    state["clean_df"] = clean_df
    state["audit_log"] = audit_log
    state["current_agent"] = "cleaning_complete"

    logger.info(
        f"Cleaning complete: {len(audit_log)} actions logged, "
        f"{len(clean_df)} rows remaining (was {len(raw_df)})"
    )
    return state
