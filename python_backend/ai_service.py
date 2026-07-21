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

# OpenAI-style tool schemas for Groq native tool calling.
# Mirrors the Gemini glm.FunctionDeclaration list below.
GROQ_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_statistics",
            "description": "Calculate statistical summary (mean, median, std, min, max, quartiles) for numeric columns",
            "parameters": {
                "type": "object",
                "properties": {
                    "columns": {
                        "type": "string",
                        "description": "Comma-separated column names to analyze"
                    }
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
            "name": "create_visualization",
            "description": "Create charts: histogram, scatter, line, bar, box, violin, heatmap, correlation, pie",
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "description": "Type: histogram, scatter, line, bar, box, violin, heatmap, correlation, pie"
                    },
                    "x_column": {"type": "string", "description": "Column for X-axis"},
                    "y_column": {"type": "string", "description": "Column for Y-axis"},
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
            "description": "Clean dataset: handle missing values, outliers, duplicates",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Action: handle_missing, remove_outliers, remove_duplicates"
                    },
                    "method": {
                        "type": "string",
                        "description": "Method: mean, median, drop, iqr, zscore"
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "show_data_preview",
            "description": "Display the current dataset table to show the user the data",
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
                    "columns": {
                        "type": "string",
                        "description": "Comma-separated column names to remove"
                    }
                },
                "required": ["columns"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "filter_rows",
            "description": "Filter/keep only rows that match a condition, removing all others",
            "parameters": {
                "type": "object",
                "properties": {
                    "column": {"type": "string", "description": "Column name to filter on"},
                    "operator": {
                        "type": "string",
                        "description": "Operator: >, <, ==, !=, >=, <=, contains"
                    },
                    "value": {"type": "string", "description": "Value to compare against"}
                },
                "required": ["column", "operator", "value"]
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


class AIService:
    def __init__(self, data_processor: DataProcessor):
        self.data_processor = data_processor
        self.gemini_available = bool(GEMINI_API_KEY)
        self.groq_available = bool(GROQ_API_KEY)

        if GEMINI_API_KEY:
            tool = glm.Tool(
                function_declarations=[
                    glm.FunctionDeclaration(
                        name="get_statistics",
                        description="Calculate statistical summary (mean, median, std, min, max, quartiles) for numeric columns",
                        parameters=glm.Schema(
                            type=glm.Type.OBJECT,
                            properties={
                                "columns": glm.Schema(
                                    type=glm.Type.STRING,
                                    description="Comma-separated column names to analyze"
                                )
                            }
                        )
                    ),
                    glm.FunctionDeclaration(
                        name="detect_missing_values",
                        description="Show all columns that have missing/null values with counts and percentages",
                        parameters=glm.Schema(
                            type=glm.Type.OBJECT,
                            properties={}
                        )
                    ),
                    glm.FunctionDeclaration(
                        name="create_visualization",
                        description="Create charts: histogram, scatter, line, bar, box, violin, heatmap, correlation, pie",
                        parameters=glm.Schema(
                            type=glm.Type.OBJECT,
                            properties={
                                "chart_type": glm.Schema(
                                    type=glm.Type.STRING,
                                    description="Type: histogram, scatter, line, bar, heatmap, correlation, pie"
                                ),
                                "x_column": glm.Schema(
                                    type=glm.Type.STRING,
                                    description="Column for X-axis"
                                ),
                                "y_column": glm.Schema(
                                    type=glm.Type.STRING,
                                    description="Column for Y-axis"
                                ),
                                "title": glm.Schema(
                                    type=glm.Type.STRING,
                                    description="Chart title"
                                )
                            },
                            required=["chart_type"]
                        )
                    ),
                    glm.FunctionDeclaration(
                        name="clean_data",
                        description="Clean dataset: handle missing values, outliers, duplicates",
                        parameters=glm.Schema(
                            type=glm.Type.OBJECT,
                            properties={
                                "action": glm.Schema(
                                    type=glm.Type.STRING,
                                    description="Action: handle_missing, remove_outliers, remove_duplicates"
                                ),
                                "method": glm.Schema(
                                    type=glm.Type.STRING,
                                    description="Method: mean, median, drop, iqr, zscore"
                                )
                            },
                            required=["action"]
                        )
                    ),
                    glm.FunctionDeclaration(
                        name="show_data_preview",
                        description="Display the current dataset table to show the user the data",
                        parameters=glm.Schema(
                            type=glm.Type.OBJECT,
                            properties={}
                        )
                    ),
                    glm.FunctionDeclaration(
                        name="remove_columns",
                        description="Remove/delete one or more columns from the dataset permanently",
                        parameters=glm.Schema(
                            type=glm.Type.OBJECT,
                            properties={
                                "columns": glm.Schema(
                                    type=glm.Type.STRING,
                                    description="Comma-separated column names to remove"
                                )
                            },
                            required=["columns"]
                        )
                    ),
                    glm.FunctionDeclaration(
                        name="filter_rows",
                        description="Filter/keep only rows that match a condition, removing all others",
                        parameters=glm.Schema(
                            type=glm.Type.OBJECT,
                            properties={
                                "column": glm.Schema(
                                    type=glm.Type.STRING,
                                    description="Column name to filter on"
                                ),
                                "operator": glm.Schema(
                                    type=glm.Type.STRING,
                                    description="Operator: >, <, ==, !=, >=, <=, contains"
                                ),
                                "value": glm.Schema(
                                    type=glm.Type.STRING,
                                    description="Value to compare against"
                                )
                            },
                            required=["column", "operator", "value"]
                        )
                    ),
                    glm.FunctionDeclaration(
                        name="run_full_analysis",
                        description="Run the full multi-agent analysis pipeline: profile the dataset, diagnose quality issues, clean a working copy, auto-generate charts, and produce an insight summary. Use when the user asks to analyze, explore, audit, or summarize the whole dataset.",
                        parameters=glm.Schema(
                            type=glm.Type.OBJECT,
                            properties={}
                        )
                    )
                ]
            )
            self.model = genai.GenerativeModel(
                'gemini-2.5-flash',
                tools=[tool]
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
            result = self.data_processor.calculate_statistics(session_id, columns_list)

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
            df = self.data_processor.get_dataframe(session_id)
            col = str(function_args['column'])
            op = str(function_args['operator'])
            val = str(function_args['value'])

            if col not in df.columns:
                return {
                    "result": {
                        "error": f"Column '{col}' not found in dataset. Available columns: {', '.join(df.columns.tolist())}"
                    },
                    "chart_data": None,
                    "data_preview": None
                }

            try:
                if df[col].dtype in ['int64', 'float64']:
                    val = float(val)
            except ValueError:
                return {
                    "result": {"error": f"Cannot convert '{val}' to number for column '{col}'"},
                    "chart_data": None,
                    "data_preview": None
                }

            import pandas as pd
            try:
                if op == '>':
                    df_filtered = pd.DataFrame(df[df[col] > val])
                elif op == '<':
                    df_filtered = pd.DataFrame(df[df[col] < val])
                elif op == '==':
                    df_filtered = pd.DataFrame(df[df[col] == val])
                elif op == '!=':
                    df_filtered = pd.DataFrame(df[df[col] != val])
                elif op == '>=':
                    df_filtered = pd.DataFrame(df[df[col] >= val])
                elif op == '<=':
                    df_filtered = pd.DataFrame(df[df[col] <= val])
                elif op == 'contains':
                    df_filtered = pd.DataFrame(df[df[col].astype(str).str.contains(re.escape(str(val)), case=False)])
                else:
                    return {
                        "result": {"error": f"Unsupported operator '{op}'. Use: >, <, ==, !=, >=, <=, contains"},
                        "chart_data": None,
                        "data_preview": None
                    }

                self.data_processor.update_dataframe(session_id, df_filtered)
                data_preview = self.data_processor._create_preview(df_filtered, max_rows=100)
                result = {
                    "message": f"✓ Kept {len(df_filtered)} rows where {col} {op} {val} (removed {len(df) - len(df_filtered)} rows)",
                    "filtered_rows": len(df_filtered),
                    "original_rows": len(df),
                    "removed_rows": len(df) - len(df_filtered)
                }
            except Exception:
                result = {"error": "Filter operation failed"}

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
1. ALWAYS PERFORM THE ACTION - never just give instructions or suggestions
2. When user says "remove/delete column X" → CALL remove_columns immediately
3. When user says "filter/keep/show rows where..." → CALL filter_rows immediately
4. When user says "remove duplicates" → CALL clean_data with action='remove_duplicates'
5. When user says "handle/fill/drop missing values" → CALL clean_data with action='handle_missing'
6. When user says "remove outliers" → CALL clean_data with action='remove_outliers'
7. When user says "create/show visualization" → CALL create_visualization
8. For questions about data → Answer directly using the actual data shown
9. After ANY operation → Confirm what you did and show the results
10. NEVER say "you can do X" or "try doing Y" - JUST DO IT
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
2. When user says "remove/delete column X" → CALL remove_columns immediately
3. When user says "filter/keep/show rows where..." → CALL filter_rows immediately
4. When user says "remove duplicates" → CALL clean_data with action='remove_duplicates'
5. When user says "handle/fill/drop missing values" → CALL clean_data with action='handle_missing'
6. When user says "remove outliers" → CALL clean_data with action='remove_outliers'
7. When user says "create/show visualization/chart" → CALL create_visualization
8. When user says "analyze/explore/audit/summarize the dataset" → CALL run_full_analysis
9. For questions about data → Answer directly using the actual data shown, without calling tools
10. NEVER say "you can do X" or "try doing Y" - JUST DO IT
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
