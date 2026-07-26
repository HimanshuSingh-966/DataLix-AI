"""Insight Agent — calls LLM to generate business insights.

Reads the output of all previous agents (schema, quality report, audit log, charts)
and asks the LLM to generate a markdown business summary.
Uses langchain-google-genai (Gemini) with a fallback to langchain-groq.
"""

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger("datalix.agents.insight")


def _format_prompt(state: dict) -> str:
    """Format pipeline state into a text prompt for the LLM."""
    clean_df = state.get("clean_df")
    schema = state.get("schema", {})
    quality = state.get("quality_report", {})
    audit = state.get("audit_log", [])
    charts = state.get("charts", [])

    if clean_df is None:
        return "No data available."

    rows = len(clean_df)
    cols = len(clean_df.columns)
    score = quality.get("overall_score", 0)

    # Schema summary
    schema_str = ", ".join([f"{c} ({i.get('dtype')})" for c, i in list(schema.items())[:15]])
    if len(schema) > 15:
        schema_str += f" ... and {len(schema)-15} more"

    # Quality issues (top 3)
    issues = quality.get("issues", [])[:3]
    issues_str = "\n".join([f"- {i['severity'].upper()}: {i['description']}" for i in issues]) or "None"

    # Audit log (top 5 actions)
    audit_str = "\n".join([f"- {a['action']} on {a['column']}: {a['reason']}" for a in audit[:5]]) or "No cleaning needed."

    # Charts
    charts_str = "\n".join([f"- {c['title']}: {c['description']}" for c in charts]) or "No charts generated."

    prompt = f"""
You are an expert Data Scientist. Analyze this dataset and provide a brief, insightful business summary.

# Dataset Profile
- Shape: {rows} rows, {cols} columns
- Columns: {schema_str}
- Data Quality Score: {score}/100

# Top Quality Issues Detected
{issues_str}

# Cleaning Actions Taken
{audit_str}

# Visualizations Generated
{charts_str}

Please provide a markdown summary with 3 sections:
1. **Executive Summary**: 2 sentences explaining what this dataset is likely about.
2. **Data Health**: 1 sentence summarizing its quality and the impact of the cleaning actions.
3. **Key Findings to Explore**: 2-3 bullet points on what the user should look at in the generated charts or data.

Keep it concise, professional, and actionable. Do not output anything outside of the markdown.
"""
    return prompt


def insight_node(state: dict) -> dict:
    """Generate business insights using LangChain + Gemini/Groq."""
    
    # 1. Check if LLM calls are disabled via env var (useful for testing)
    if os.getenv("DISABLE_LLM_INSIGHTS", "false").lower() == "true":
        logger.info("LLM insights disabled via env var. Returning static summary.")
        state["insight_summary"] = "Insight generation disabled. Enable LLM to see insights."
        state["current_agent"] = "insight_complete"
        return state

    prompt = _format_prompt(state)
    logger.info("Insight agent calling LLM...")

    try:
        # Try Gemini first
        from langchain_google_genai import ChatGoogleGenerativeAI
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        if gemini_api_key:
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash", 
                temperature=0.2, 
                google_api_key=gemini_api_key
            )
            response = llm.invoke(prompt)
            state["insight_summary"] = response.content
            logger.info("Insight generated via Gemini.")
            state["current_agent"] = "insight_complete"
            return state
            
    except Exception as e:
        logger.warning(f"Gemini failed: {type(e).__name__}. Falling back to Groq...")

    try:
        # Fallback to Groq
        from langchain_groq import ChatGroq
        groq_api_key = os.getenv("GROQ_API_KEY")
        
        if groq_api_key:
            llm = ChatGroq(
                model="llama-3.3-70b-versatile",
                temperature=0.2,
                api_key=groq_api_key
            )
            response = llm.invoke(prompt)
            state["insight_summary"] = response.content
            logger.info("Insight generated via Groq.")
            state["current_agent"] = "insight_complete"
            return state
            
    except Exception as e:
        logger.warning(f"Groq failed: {type(e).__name__}. Falling back to static.")

    # Ultimate fallback
    score = state.get("quality_report", {}).get("overall_score", 0)
    clean_df = state.get("clean_df")
    row_count = len(clean_df) if clean_df is not None else 0
    col_count = len(clean_df.columns) if clean_df is not None else 0
    state["insight_summary"] = f"""
## Executive Summary
This dataset contains {row_count} rows and {col_count} columns.

## Data Health
The dataset received a quality score of {score}/100. Check the audit log for details on automated cleaning actions performed.

## Key Findings to Explore
- Review the generated charts to identify trends and outliers.
- Ask questions in the chat to dive deeper into specific columns.
"""
    logger.info("Insight generated via static fallback.")
    state["current_agent"] = "insight_complete"
    return state
