"""Visualization Agent — auto-selects and generates relevant Plotly charts.

Chart selection logic (from the plan):
  - datetime + numeric → line chart
  - categorical (<10 unique) → bar chart (value counts)
  - numeric → histogram
  - 2+ numeric → correlation heatmap
  - 1 categorical + 1 numeric → box plot
  - Cap at 5 charts total
"""

import json
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger("datalix.agents.visualization")


def visualization_node(state: dict) -> dict:
    """Auto-select and generate Plotly charts from clean_df.

    Reads: state["clean_df"], state["schema"]
    Writes: state["charts"]
    """
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go

    clean_df = state.get("clean_df")
    schema = state.get("schema", {})

    if clean_df is None:
        state["error"] = "No cleaned DataFrame available for visualization."
        state["current_agent"] = "visualization_error"
        return state

    logger.info(f"Visualization agent starting: {len(clean_df)} rows, {len(clean_df.columns)} cols")

    charts = []

    # Classify columns
    numeric_cols = [
        col for col, info in schema.items()
        if info.get("dtype") == "numeric" and col in clean_df.columns
    ]
    categorical_cols = [
        col for col, info in schema.items()
        if info.get("dtype") == "categorical" and col in clean_df.columns
        and info.get("unique_count", 0) < 10
    ]
    datetime_cols = [
        col for col, info in schema.items()
        if info.get("dtype") in ("datetime", "datetime_string") and col in clean_df.columns
    ]

    def _safe_chart(fn, chart_type, title, description):
        """Wrap chart creation in try/except to avoid single chart failures killing the pipeline."""
        try:
            fig = fn()
            fig.update_layout(
                template="plotly_white",
                font=dict(family="Inter, sans-serif"),
                title_x=0.5,
            )
            charts.append({
                "type": chart_type,
                "title": title,
                "description": description,
                "figure": json.loads(fig.to_json()),
            })
            logger.info(f"Generated {chart_type}: {title}")
        except Exception as e:
            logger.warning(f"Failed to generate {chart_type} chart: {type(e).__name__}")

    # 1. datetime + numeric → line chart
    if datetime_cols and numeric_cols:
        dt_col = datetime_cols[0]
        num_col = numeric_cols[0]
        # Try to parse datetime if stored as string
        df_viz = clean_df.copy()
        if schema.get(dt_col, {}).get("dtype") == "datetime_string":
            try:
                df_viz[dt_col] = pd.to_datetime(df_viz[dt_col], errors="coerce")
            except Exception:
                pass

        _safe_chart(
            lambda: px.line(
                df_viz.sort_values(dt_col),
                x=dt_col, y=num_col,
                title=f"{num_col} over {dt_col}",
            ),
            "line",
            f"{num_col} over {dt_col}",
            f"Time series showing {num_col} trends across {dt_col}",
        )

    # 2. categorical (<10 unique) → bar chart
    for cat_col in categorical_cols[:2]:  # Max 2 bar charts
        if len(charts) >= 5:
            break
        vc = clean_df[cat_col].value_counts().head(10)
        _safe_chart(
            lambda vc=vc, cat_col=cat_col: px.bar(
                x=vc.index.astype(str), y=vc.values,
                title=f"Distribution of {cat_col}",
                labels={"x": cat_col, "y": "Count"},
            ),
            "bar",
            f"Distribution of {cat_col}",
            f"Shows value counts for each category in {cat_col}",
        )

    # 3. numeric → histogram (first numeric col not already charted)
    for num_col in numeric_cols[:2]:
        if len(charts) >= 5:
            break
        _safe_chart(
            lambda num_col=num_col: px.histogram(
                clean_df, x=num_col,
                title=f"Distribution of {num_col}",
            ),
            "histogram",
            f"Distribution of {num_col}",
            f"Histogram showing the frequency distribution of {num_col}",
        )

    # 4. 2+ numeric → correlation heatmap
    if len(numeric_cols) >= 2 and len(charts) < 5:
        corr_cols = numeric_cols[:10]  # Limit to 10 cols for readability
        _safe_chart(
            lambda: px.imshow(
                clean_df[corr_cols].corr(),
                text_auto=".2f",
                title="Correlation Heatmap",
                color_continuous_scale="RdBu_r",
                aspect="auto",
                labels=dict(color="Correlation"),
            ),
            "heatmap",
            "Correlation Heatmap",
            f"Correlation matrix across {len(corr_cols)} numeric columns",
        )

    # 5. 1 categorical + 1 numeric → box plot
    if categorical_cols and numeric_cols and len(charts) < 5:
        cat_col = categorical_cols[0]
        num_col = numeric_cols[0]
        _safe_chart(
            lambda: px.box(
                clean_df, x=cat_col, y=num_col,
                title=f"{num_col} by {cat_col}",
            ),
            "box",
            f"{num_col} by {cat_col}",
            f"Box plot showing {num_col} distribution grouped by {cat_col}",
        )

    # Cap at 5
    charts = charts[:5]

    state["charts"] = charts
    state["current_agent"] = "visualization_complete"

    logger.info(f"Visualization complete: {len(charts)} charts generated")
    return state
