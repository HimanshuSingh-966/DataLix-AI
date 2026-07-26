import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
import google.generativeai as genai
import google.ai.generativelanguage as glm
from groq import Groq
from data_processor import DataProcessor
from statistics_module import calculate_statistics, calculate_correlation
from visualizations import create_visualization
from data_cleaning import clean_dataset, handle_missing_values
from ml_analysis import perform_ml_analysis

logger = logging.getLogger("datalix.ai")

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("Gemini AI configured")
else:
    logger.warning("GEMINI_API_KEY not set")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)
    logger.info("Groq AI configured")
else:
    groq_client = None
    logger.warning("GROQ_API_KEY not set")

if not GEMINI_API_KEY and not GROQ_API_KEY:
    logger.error("No AI provider configured. Set GEMINI_API_KEY or GROQ_API_KEY")

# Single source of truth for tool schemas (OpenAI JSON-schema format).
# The Gemini declarations are generated from this list by _build_gemini_tool().
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_statistics",
            "description": "Statistical summary (mean, median, std, min, max, quartiles) for numeric columns. Use group_by to compare groups, e.g. average marks per department.",
            "parameters": {
                "type": "object",
                "properties": {
                    "columns": {"type": "string", "description": "Comma-separated column names to analyze (all numeric columns if omitted)"},
                    "group_by": {"type": "string", "description": "Categorical column to group by, e.g. 'Department' for per-department stats"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "detect_missing_values",
            "description": "Show all columns that have missing/null values with counts and percentages",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_correlation",
            "description": "Correlation matrix between numeric columns, with a heatmap",
            "parameters": {
                "type": "object",
                "properties": {
                    "columns": {"type": "string", "description": "Comma-separated numeric columns (all if omitted)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_visualization",
            "description": "Create a chart. For 'how many X per Y' use aggregation='count' with x_column only. For 'average/total X by Y' set y_column and aggregation. NEVER use an ID column as y_column.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {"type": "string", "description": "One of: histogram, scatter, line, bar, box, violin, heatmap, correlation, pie"},
                    "x_column": {"type": "string", "description": "Column for X-axis (category for bar/pie)"},
                    "y_column": {"type": "string", "description": "Numeric column for Y-axis. OMIT for count charts."},
                    "aggregation": {"type": "string", "description": "How to aggregate rows per x value: count, sum, mean, median, min, max. Use 'count' for 'number of rows per category'."},
                    "title": {"type": "string", "description": "Chart title"}
                },
                "required": ["chart_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clean_data",
            "description": "Clean dataset: handle missing values, outliers, duplicates. THIS MODIFIES THE DATA.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "Action: handle_missing, remove_outliers, remove_duplicates"},
                    "method": {"type": "string", "description": "Method: mean, median, drop, iqr, zscore"}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "show_data_preview",
            "description": "Display the current dataset table to the user",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "show_duplicates",
            "description": "Show duplicated rows WITHOUT removing them (inspection only)",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remove_columns",
            "description": "Remove/delete one or more columns from the dataset permanently",
            "parameters": {
                "type": "object",
                "properties": {
                    "columns": {"type": "string", "description": "Comma-separated column names to remove"}
                },
                "required": ["columns"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "filter_rows",
            "description": "Find rows matching one or more conditions. Default mode 'view' just SHOWS matching rows without changing the dataset — use it for 'show me...' requests. Only use mode 'permanent' when the user explicitly wants to delete/keep-only rows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "conditions": {
                        "type": "array",
                        "description": "One or more filter conditions",
                        "items": {
                            "type": "object",
                            "properties": {
                                "column": {"type": "string", "description": "Column name"},
                                "operator": {"type": "string", "description": "One of: >, <, ==, !=, >=, <=, contains"},
                                "value": {"type": "string", "description": "Value to compare against (dates as YYYY-MM-DD)"}
                            },
                            "required": ["column", "operator", "value"]
                        }
                    },
                    "combine": {"type": "string", "description": "How to combine multiple conditions: 'and' (default) or 'or'"},
                    "mode": {"type": "string", "description": "'view' (default, dataset unchanged) or 'permanent' (keeps only matching rows)"}
                },
                "required": ["conditions"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sort_data",
            "description": "Sort by a column. With limit, shows the top N rows WITHOUT changing the dataset — use for 'top 5 by marks' or 'who has the highest X'. Without limit, permanently reorders the dataset.",
            "parameters": {
                "type": "object",
                "properties": {
                    "column": {"type": "string", "description": "Column to sort by"},
                    "order": {"type": "string", "description": "'desc' (default) or 'asc'"},
                    "limit": {"type": "integer", "description": "Show only the top N rows (view only, no mutation)"}
                },
                "required": ["column"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_column",
            "description": "Create a new derived column from an arithmetic formula over existing columns, e.g. name='Total' formula='Price * Quantity'",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "New column name"},
                    "formula": {"type": "string", "description": "Arithmetic formula using existing column names, e.g. 'Marks / 100 * Attendance'"}
                },
                "required": ["name", "formula"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "rename_column",
            "description": "Rename a column",
            "parameters": {
                "type": "object",
                "properties": {
                    "old_name": {"type": "string", "description": "Current column name"},
                    "new_name": {"type": "string", "description": "New column name"}
                },
                "required": ["old_name", "new_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reset_dataset",
            "description": "Undo ALL modifications and restore the dataset to its original uploaded state. Use when the user says undo, revert, reset, or start over.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ml_analysis",
            "description": "Machine learning analysis: clustering, anomaly_detection, dimensionality_reduction, feature_importance",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis_type": {"type": "string", "description": "One of: clustering, anomaly_detection, dimensionality_reduction, feature_importance"}
                },
                "required": ["analysis_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_full_analysis",
            "description": "Run the full multi-agent analysis pipeline: profile the dataset, diagnose quality issues, clean a working copy, auto-generate charts, and produce an insight summary. Use when the user asks to analyze, explore, audit, or summarize the whole dataset.",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]

# Backwards-compatible alias
GROQ_TOOLS = TOOLS

_GLM_TYPE_MAP = {
    "object": glm.Type.OBJECT,
    "string": glm.Type.STRING,
    "integer": glm.Type.INTEGER,
    "number": glm.Type.NUMBER,
    "boolean": glm.Type.BOOLEAN,
    "array": glm.Type.ARRAY,
}


def _to_glm_schema(js: Dict[str, Any]) -> "glm.Schema":
    """Convert an OpenAI-style JSON schema fragment to a Gemini glm.Schema."""
    schema = glm.Schema(type=_GLM_TYPE_MAP.get(js.get("type", "string"), glm.Type.STRING))
    if js.get("description"):
        schema.description = js["description"]
    if js.get("type") == "object":
        for key, prop in (js.get("properties") or {}).items():
            schema.properties[key] = _to_glm_schema(prop)
        for req in js.get("required", []):
            schema.required.append(req)
    if js.get("type") == "array" and js.get("items"):
        schema.items = _to_glm_schema(js["items"])
    return schema


def _build_gemini_tool() -> "glm.Tool":
    """Generate the Gemini tool declarations from TOOLS (single schema source)."""
    return glm.Tool(
        function_declarations=[
            glm.FunctionDeclaration(
                name=t["function"]["name"],
                description=t["function"]["description"],
                parameters=_to_glm_schema(t["function"]["parameters"]),
            )
            for t in TOOLS
        ]
    )



class AIService:
    def __init__(self, data_processor: DataProcessor):
        self.data_processor = data_processor
        self.gemini_available = bool(GEMINI_API_KEY)
        self.groq_available = bool(GROQ_API_KEY)

        if GEMINI_API_KEY:
            self.model = genai.GenerativeModel(
                'gemini-2.5-flash',
                tools=[_build_gemini_tool()]
            )
        else:
            self.model = None

    async def process_message(
        self,
        session_id: str,
        message: str,
        user_id: str,
        provider: str = "auto"
    ) -> Dict[str, Any]:
        if provider == "auto":
            if self.groq_available:
                provider = "groq"
            elif self.gemini_available:
                provider = "gemini"
            else:
                return {
                    "message": "⚠️ No AI provider configured. Please set GEMINI_API_KEY or GROQ_API_KEY.",
                    "function_calls": None,
                    "results": None
                }

        if provider == "groq" and self.groq_available:
            return await self._process_with_groq(session_id, message, user_id)
        elif provider == "gemini" and self.gemini_available:
            return await self._process_with_gemini(session_id, message, user_id)
        else:
            return {
                "message": f"⚠️ {provider.capitalize()} is not available. Please configure the API key.",
                "function_calls": None,
                "results": None
            }

    def _execute_tool(
        self,
        session_id: str,
        function_name: str,
        function_args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single tool call against the DataProcessor.

        Shared by the Gemini and Groq paths.

        Returns:
            {"result": dict, "chart_data": dict|None, "data_preview": dict|None}
        """
        result = None
        chart_data = None
        data_preview = None

        if function_name == "get_statistics":
            cols = function_args.get('columns')
            columns_list = [c.strip() for c in str(cols).split(',')] if cols else None
            result = self.data_processor.calculate_statistics(
                session_id, columns_list, group_by=function_args.get('group_by') or None
            )

        elif function_name == "detect_missing_values":
            result = self.data_processor.detect_missing_values(session_id)

        elif function_name == "get_correlation":
            cols = function_args.get('columns')
            columns_list = [c.strip() for c in str(cols).split(',')] if cols else None
            result = self.data_processor.calculate_correlation(session_id, columns_list)
            chart_data = self.data_processor.create_visualization(
                session_id,
                chart_type="correlation",
                parameters={"title": "Correlation Matrix"}
            )

        elif function_name == "create_visualization":
            chart_data = self.data_processor.create_visualization(
                session_id,
                chart_type=str(function_args['chart_type']),
                x_column=str(function_args.get('x_column')) if function_args.get('x_column') else None,
                y_column=str(function_args.get('y_column')) if function_args.get('y_column') else None,
                parameters=dict(function_args)
            )
            result = {"visualization": "created"}

        elif function_name == "clean_data":
            result = self.data_processor.clean_data(
                session_id,
                parameters=dict(function_args)
            )

        elif function_name == "show_data_preview":
            try:
                df = self.data_processor.get_dataframe(session_id)
                data_preview = self.data_processor._create_preview(df, max_rows=100)
                result = {"message": "Showing data preview"}
            except Exception:
                result = {"error": "No dataset loaded"}

        elif function_name == "remove_columns":
            df = self.data_processor.get_dataframe(session_id)
            columns_to_remove = [col.strip() for col in str(function_args['columns']).split(',')]

            existing_cols = [col for col in columns_to_remove if col in df.columns]
            invalid_cols = [col for col in columns_to_remove if col not in df.columns]

            if not existing_cols:
                result = {
                    "error": f"Column(s) not found in dataset: {', '.join(invalid_cols)}. Available columns: {', '.join(df.columns.tolist())}"
                }
            else:
                df_updated = df.drop(columns=existing_cols)
                self.data_processor.update_dataframe(session_id, df_updated)

                result_msg = f"✓ Removed {len(existing_cols)} column(s): {', '.join(existing_cols)}"
                if invalid_cols:
                    result_msg += f". Note: These columns were not found: {', '.join(invalid_cols)}"

                result = {
                    "message": result_msg,
                    "removed_columns": existing_cols,
                    "remaining_columns": len(df_updated.columns),
                    "remaining_rows": len(df_updated)
                }

        elif function_name == "filter_rows":
            conditions = function_args.get('conditions')
            if not conditions and function_args.get('column'):
                # legacy single-condition shape
                conditions = [{
                    "column": function_args.get('column'),
                    "operator": function_args.get('operator'),
                    "value": function_args.get('value'),
                }]
            outcome = self.data_processor.filter_rows(
                session_id,
                conditions or [],
                combine=str(function_args.get('combine') or 'and').lower(),
                mode=str(function_args.get('mode') or 'view').lower(),
            )
            data_preview = outcome.pop('preview', None)
            result = outcome

        elif function_name == "sort_data":
            limit = function_args.get('limit')
            outcome = self.data_processor.sort_data(
                session_id,
                column=str(function_args['column']),
                order=str(function_args.get('order') or 'desc'),
                limit=int(limit) if limit else None,
            )
            data_preview = outcome.pop('preview', None)
            result = outcome

        elif function_name == "add_column":
            outcome = self.data_processor.add_column(
                session_id,
                name=str(function_args['name']),
                formula=str(function_args['formula']),
            )
            data_preview = outcome.pop('preview', None)
            result = outcome

        elif function_name == "rename_column":
            outcome = self.data_processor.rename_column(
                session_id,
                old_name=str(function_args['old_name']),
                new_name=str(function_args['new_name']),
            )
            data_preview = outcome.pop('preview', None)
            result = outcome

        elif function_name == "show_duplicates":
            outcome = self.data_processor.get_duplicates(session_id)
            data_preview = outcome.pop('preview', None)
            result = outcome

        elif function_name == "reset_dataset":
            outcome = self.data_processor.reset_dataset(session_id)
            data_preview = outcome.pop('preview', None)
            result = outcome

        elif function_name == "ml_analysis":
            result = self.data_processor.ml_analysis(
                session_id,
                analysis_type=str(function_args['analysis_type']),
                parameters=dict(function_args)
            )
            if result.get('visualization'):
                chart_data = result['visualization']

        elif function_name == "run_full_analysis":
            from agents import run_pipeline
            pipeline_state = run_pipeline(session_id)

            if pipeline_state.get("error"):
                result = {"error": pipeline_state["error"]}
            else:
                # Surface the first auto-generated chart; the rest are described in the summary
                charts = pipeline_state.get("charts", [])
                if charts:
                    fig = charts[0].get("figure", {})
                    chart_data = {
                        "data": fig.get("data", []),
                        "layout": fig.get("layout", {}),
                        "config": {"responsive": True, "displayModeBar": True}
                    }
                result = {
                    "quality_report": pipeline_state.get("quality_report", {}),
                    "audit_log": pipeline_state.get("audit_log", []),
                    "charts_generated": [c.get("title") for c in charts],
                    "insight_summary": pipeline_state.get("insight_summary", "")
                }

        else:
            result = {"error": f"Unknown function: {function_name}"}

        return {"result": result, "chart_data": chart_data, "data_preview": data_preview}

    async def _process_with_gemini(
        self,
        session_id: str,
        message: str,
        user_id: str
    ) -> Dict[str, Any]:
        if not self.model:
            return {
                "message": "⚠️ Gemini not configured.",
                "function_calls": None,
                "results": None
            }

        try:
            df = self.data_processor.get_dataframe(session_id)
            session = self.data_processor.sessions.get(session_id, {})
            original_rows = session.get("original_rows", len(df))
            original_cols = session.get("original_columns", len(df.columns))

            missing_info = []
            for col in df.columns:
                missing_count = df[col].isnull().sum()
                if missing_count > 0:
                    missing_pct = (missing_count / len(df)) * 100
                    missing_info.append(f"{col}: {missing_count} ({missing_pct:.1f}%)")

            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            stats_preview = []
            for col in numeric_cols[:5]:
                stats_preview.append(f"{col}: min={df[col].min():.2f}, max={df[col].max():.2f}, mean={df[col].mean():.2f}")

            if original_rows != len(df) or original_cols != len(df.columns):
                dimension_info = f"""
CURRENT DATASET (after filtering/modifications):
- Current rows: {len(df)}
- Current columns: {len(df.columns)}

ORIGINAL DATASET (before any modifications):
- Original rows: {original_rows}
- Original columns: {original_cols}"""
            else:
                dimension_info = f"""
CURRENT DATASET:
- Total rows: {len(df)}
- Total columns: {len(df.columns)}"""

            dataset_context = f"""
You are a data analysis assistant. The user has a dataset loaded and you can perform operations on it.

{dimension_info}
- File size: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB

COLUMNS ({len(df.columns)} total):
{chr(10).join([f"- {col} ({df[col].dtype}): {df[col].nunique()} unique values" for col in df.columns])}

MISSING VALUES:
{chr(10).join([f"- {info}" for info in missing_info]) if missing_info else "- No missing values found"}

NUMERIC COLUMNS PREVIEW:
{chr(10).join([f"- {stat}" for stat in stats_preview]) if stats_preview else "- No numeric columns"}

DATA PREVIEW (first 3 rows):
{df.head(3).to_string()}

USER REQUEST: {message}

CRITICAL INSTRUCTIONS - YOU ARE AN ACTION-ORIENTED ASSISTANT:
1. ALWAYS PERFORM THE ACTION using the provided tools - never just give instructions or suggestions
2. "how many rows/records per <category>" → create_visualization with chart_type='bar', x_column=<category>, aggregation='count', NO y_column. NEVER use an ID column (Student_ID, Order_ID, ...) as y_column.
3. "average/total <numeric> by <category>" chart → create_visualization with y_column=<numeric> and aggregation='mean' or 'sum'
4. "compare groups" or "average X per Y" as numbers → get_statistics with group_by=<category>
5. "show/find rows where..." → filter_rows with mode='view' (default - does NOT change the data). Use mode='permanent' ONLY when the user explicitly says delete/remove/keep only those rows.
6. "top N by X" or "who has the highest/lowest X" → sort_data with column=X, limit=N (view only, answer from the returned records)
7. "add/create/compute a new column" → add_column; "rename column" → rename_column
8. "undo/revert/reset/start over" → reset_dataset
9. "show duplicates" → show_duplicates (inspect only); "remove duplicates" → clean_data with action='remove_duplicates'
10. "remove/delete column X" → remove_columns; missing values → clean_data action='handle_missing'; outliers → clean_data action='remove_outliers'
11. "analyze/explore/audit/summarize the whole dataset" → run_full_analysis
12. For factual questions about specific values (max, min, who, which) → use sort_data or get_statistics instead of reading the preview - the preview may be truncated
13. After ANY operation confirm what you did with the results. NEVER say "you can do X" or "try doing Y" - JUST DO IT
"""
        except Exception as e:
            dataset_context = f"User message: {message}\n\nNote: No dataset loaded yet. If they're asking about data operations, suggest uploading a dataset first."

        try:
            chat = self.model.start_chat()
            response = chat.send_message(dataset_context)

            function_calls_made = []
            results = []
            chart_data = None
            data_preview = None

            if response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        fc = part.function_call
                        function_name = fc.name
                        function_args = dict(fc.args)

                        function_calls_made.append(function_name)

                        try:
                            outcome = self._execute_tool(session_id, function_name, function_args)
                            if outcome["result"] is not None:
                                results.append(outcome["result"])
                            if outcome["chart_data"] is not None:
                                chart_data = outcome["chart_data"]
                            if outcome["data_preview"] is not None:
                                data_preview = outcome["data_preview"]
                        except Exception as e:
                            logger.error(f"Gemini function execution failed: {type(e).__name__}")
                            results.append({"error": "Operation failed"})

            try:
                ai_message = response.text if response.text else ""
            except ValueError:
                ai_message = ""

            if not ai_message and function_calls_made:
                follow_up = chat.send_message(
                    f"I executed these functions: {', '.join(function_calls_made)}. "
                    f"Results: {json.dumps(results, default=str)}. "
                    "Please provide a natural language summary of the results for the user."
                )
                try:
                    ai_message = follow_up.text
                except ValueError:
                    ai_message = "I've processed your request."
            elif not ai_message:
                ai_message = "I've processed your request."

            suggested_actions = self._generate_suggestions(session_id, function_calls_made)

            return {
                "message": ai_message,
                "function_calls": function_calls_made if function_calls_made else None,
                "results": results if results else None,
                "data_preview": data_preview if data_preview else None,
                "chart_data": chart_data,
                "suggested_actions": suggested_actions
            }

        except Exception as e:
            logger.error(f"Gemini processing failed: {type(e).__name__}")
            return {
                "message": "I encountered an error processing your request. Could you please rephrase?",
                "function_calls": None,
                "results": None
            }

    async def _process_with_groq(
        self,
        session_id: str,
        message: str,
        user_id: str
    ) -> Dict[str, Any]:
        if not groq_client:
            return {
                "message": "⚠️ Groq not configured.",
                "function_calls": None,
                "results": None
            }

        try:
            df = self.data_processor.get_dataframe(session_id)
            session = self.data_processor.sessions.get(session_id, {})
            original_rows = session.get("original_rows", len(df))
            original_cols = session.get("original_columns", len(df.columns))

            missing_info = []
            for col in df.columns:
                missing_count = df[col].isnull().sum()
                if missing_count > 0:
                    missing_pct = (missing_count / len(df)) * 100
                    missing_info.append(f"{col}: {missing_count} ({missing_pct:.1f}%)")

            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            stats_preview = []
            for col in numeric_cols[:5]:
                stats_preview.append(f"{col}: min={df[col].min():.2f}, max={df[col].max():.2f}, mean={df[col].mean():.2f}")

            if original_rows != len(df) or original_cols != len(df.columns):
                dimension_info = f"""
CURRENT DATASET (after filtering/modifications):
- Current rows: {len(df)}
- Current columns: {len(df.columns)}

ORIGINAL DATASET (before any modifications):
- Original rows: {original_rows}
- Original columns: {original_cols}"""
            else:
                dimension_info = f"""
CURRENT DATASET:
- Total rows: {len(df)}
- Total columns: {len(df.columns)}"""

            dataset_context = f"""
{dimension_info}

COLUMNS ({len(df.columns)} total):
{chr(10).join([f"- {col} ({df[col].dtype}): {df[col].nunique()} unique values" for col in df.columns])}

MISSING VALUES:
{chr(10).join([f"- {info}" for info in missing_info]) if missing_info else "- No missing values found"}

NUMERIC COLUMNS PREVIEW:
{chr(10).join([f"- {stat}" for stat in stats_preview]) if stats_preview else "- No numeric columns"}

DATA PREVIEW (first 3 rows):
{df.head(3).to_string()}

USER REQUEST: {message}

CRITICAL INSTRUCTIONS - YOU ARE AN ACTION-ORIENTED ASSISTANT:
1. ALWAYS PERFORM THE ACTION using the provided tools - never just give instructions or suggestions
2. "how many rows/records per <category>" → create_visualization with chart_type='bar', x_column=<category>, aggregation='count', NO y_column. NEVER use an ID column (Student_ID, Order_ID, ...) as y_column.
3. "average/total <numeric> by <category>" chart → create_visualization with y_column=<numeric> and aggregation='mean' or 'sum'
4. "compare groups" or "average X per Y" as numbers → get_statistics with group_by=<category>
5. "show/find rows where..." → filter_rows with mode='view' (default - does NOT change the data). Use mode='permanent' ONLY when the user explicitly says delete/remove/keep only those rows.
6. "top N by X" or "who has the highest/lowest X" → sort_data with column=X, limit=N (view only, answer from the returned records)
7. "add/create/compute a new column" → add_column; "rename column" → rename_column
8. "undo/revert/reset/start over" → reset_dataset
9. "show duplicates" → show_duplicates (inspect only); "remove duplicates" → clean_data with action='remove_duplicates'
10. "remove/delete column X" → remove_columns; missing values → clean_data action='handle_missing'; outliers → clean_data action='remove_outliers'
11. "analyze/explore/audit/summarize the whole dataset" → run_full_analysis
12. For factual questions about specific values (max, min, who, which) → use sort_data or get_statistics instead of reading the preview - the preview may be truncated
13. After ANY operation confirm what you did with the results. NEVER say "you can do X" or "try doing Y" - JUST DO IT
"""
        except Exception as e:
            dataset_context = f"User message: {message}\n\nNote: No dataset loaded. Suggest uploading a dataset first."

        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an action-oriented data analysis assistant. "
                        "When the user asks for an operation on their dataset, call the appropriate tool "
                        "instead of describing steps. For pure questions about the data, answer directly "
                        "from the dataset context without calling tools."
                    )
                },
                {"role": "user", "content": dataset_context}
            ]

            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                tools=GROQ_TOOLS,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=2048
            )

            choice = response.choices[0].message

            function_calls_made = []
            results = []
            chart_data = None
            data_preview = None

            if choice.tool_calls:
                # Execute each requested tool, then ask the model to summarize the results
                messages.append({
                    "role": "assistant",
                    "content": choice.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                        }
                        for tc in choice.tool_calls
                    ]
                })

                for tc in choice.tool_calls:
                    function_name = tc.function.name
                    try:
                        function_args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                    except json.JSONDecodeError:
                        function_args = {}

                    function_calls_made.append(function_name)

                    try:
                        outcome = self._execute_tool(session_id, function_name, function_args)
                        if outcome["result"] is not None:
                            results.append(outcome["result"])
                        if outcome["chart_data"] is not None:
                            chart_data = outcome["chart_data"]
                        if outcome["data_preview"] is not None:
                            data_preview = outcome["data_preview"]
                        tool_result = outcome["result"] if outcome["result"] is not None else {"status": "ok"}
                    except Exception:
                        logger.error(f"Groq tool execution failed: {function_name}")
                        tool_result = {"error": "Operation failed"}
                        results.append(tool_result)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(tool_result, default=str)[:4000]
                    })

                # Follow-up completion so the user gets a natural-language summary of what was done
                try:
                    follow_up = groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=messages,
                        temperature=0.3,
                        max_tokens=1024
                    )
                    ai_message = follow_up.choices[0].message.content or "I've processed your request."
                except Exception:
                    logger.error("Groq follow-up summary failed")
                    ai_message = "✓ Done: " + ", ".join(function_calls_made)
            else:
                ai_message = choice.content or "I've processed your request."

            suggested_actions = self._generate_suggestions(session_id, function_calls_made)

            return {
                "message": ai_message,
                "function_calls": function_calls_made if function_calls_made else None,
                "results": results if results else None,
                "data_preview": data_preview if data_preview else None,
                "chart_data": chart_data,
                "suggested_actions": suggested_actions,
                "provider": "groq"
            }

        except Exception as e:
            logger.error(f"Groq processing failed: {type(e).__name__}")
            return {
                "message": "I encountered an error processing your request. Could you please rephrase?",
                "function_calls": None,
                "results": None
            }

    def _generate_suggestions(self, session_id: str, recent_actions: List[str]) -> List[Dict[str, str]]:
        suggestions = []

        try:
            df = self.data_processor.get_dataframe(session_id)
            quality = self.data_processor.sessions[session_id].get('quality', {})

            if 'run_full_analysis' not in recent_actions:
                suggestions.append({
                    "label": "Run Full Analysis",
                    "prompt": "Run a full analysis of my dataset"
                })

            if quality.get('issues'):
                for issue in quality['issues'][:2]:
                    if issue['type'] == 'missing_values':
                        suggestions.append({
                            "label": "Handle Missing Values",
                            "prompt": "Handle missing values using mean imputation"
                        })
                    elif issue['type'] == 'duplicates':
                        suggestions.append({
                            "label": "Remove Duplicates",
                            "prompt": "Remove duplicate rows"
                        })
                    elif issue['type'] == 'outliers':
                        suggestions.append({
                            "label": "Detect Outliers",
                            "prompt": f"Detect outliers in {issue.get('column', 'numeric columns')}"
                        })

            if 'get_statistics' not in recent_actions:
                suggestions.append({
                    "label": "Show Statistics",
                    "prompt": "Show statistical summary of all columns"
                })

            if 'get_correlation' not in recent_actions:
                suggestions.append({
                    "label": "Correlation Analysis",
                    "prompt": "Show correlation matrix"
                })

            if 'create_visualization' not in recent_actions:
                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                if len(numeric_cols) >= 2:
                    suggestions.append({
                        "label": "Create Scatter Plot",
                        "prompt": f"Create scatter plot of {numeric_cols[0]} vs {numeric_cols[1]}"
                    })

            if 'ml_analysis' not in recent_actions:
                suggestions.append({
                    "label": "Cluster Analysis",
                    "prompt": "Perform K-means clustering with 3 clusters"
                })

        except Exception as e:
            suggestions = [
                {"label": "Upload Data", "prompt": "How do I upload a dataset?"},
                {"label": "Get Started", "prompt": "What can you help me with?"}
            ]

        return suggestions[:5]
