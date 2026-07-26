"""Shared state definition for the DataLix agent pipeline.

DataLixState is a TypedDict that flows through:
  ingestion → diagnosis → cleaning → visualization → insight

AuditEntry records every cleaning decision for the Audit Log UI.
"""

from typing import TypedDict, Optional, Any, List


class AuditEntry(TypedDict):
    """A single auditable cleaning action."""
    column: str
    action: str           # "imputed_median", "dropped_duplicates", "capped_outliers", etc.
    reason: str           # Human-readable explanation
    rows_affected: int
    reversible: bool
    original_stats: dict  # Before state (mean, null_count, etc.)
    new_stats: dict       # After state


class DataLixState(TypedDict):
    """Shared state flowing through all agents.

    Notes:
    - raw_df / clean_df are pandas DataFrames (not serialized).
      They are converted to dict at the API boundary only.
    - audit_log accumulates across agents (cleaning agent is the primary writer).
    - error short-circuits the pipeline via the should_continue conditional edge.
    """
    session_id: str
    raw_df: Optional[Any]           # pandas DataFrame — not serialized
    clean_df: Optional[Any]         # pandas DataFrame — not serialized
    schema: dict                    # {col: {dtype, null_count, null_pct, unique_count, ...}}
    quality_report: dict            # {overall_score, issue_count, issues: [...]}
    audit_log: List[AuditEntry]     # Every cleaning decision logged here
    charts: List[dict]              # Plotly figure dicts (JSON-serializable)
    insight_summary: str
    error: Optional[str]
    current_agent: str
