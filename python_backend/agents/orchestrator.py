"""LangGraph Orchestrator for the DataLix agent pipeline.

Defines the StateGraph and the linear workflow:
  ingestion → diagnosis → cleaning → visualization → insight
"""

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.graph import StateGraph, END
from .state import DataLixState
from .ingestion import ingestion_node
from .diagnosis import diagnosis_node
from .cleaning import cleaning_node
from .visualization import visualization_node
from .insight import insight_node

logger = logging.getLogger("datalix.agents.orchestrator")


def _should_continue(state: dict) -> str:
    """Conditional edge router. Halts pipeline if state['error'] is set."""
    if state.get("error"):
        logger.warning(f"Pipeline halted at {state.get('current_agent')} due to error: {state.get('error')}")
        return END
    return "next"


# Build the graph
workflow = StateGraph(DataLixState)

# Add nodes
workflow.add_node("ingestion", ingestion_node)
workflow.add_node("diagnosis", diagnosis_node)
workflow.add_node("cleaning", cleaning_node)
workflow.add_node("visualization", visualization_node)
workflow.add_node("insight", insight_node)

# Add edges (linear pipeline with error checking)
workflow.set_entry_point("ingestion")

workflow.add_conditional_edges("ingestion", _should_continue, {"next": "diagnosis", END: END})
workflow.add_conditional_edges("diagnosis", _should_continue, {"next": "cleaning", END: END})
workflow.add_conditional_edges("cleaning", _should_continue, {"next": "visualization", END: END})
workflow.add_conditional_edges("visualization", _should_continue, {"next": "insight", END: END})
workflow.add_conditional_edges("insight", _should_continue, {"next": END, END: END})

# Compile the graph
pipeline = workflow.compile()


def run_pipeline(session_id: str) -> dict:
    """Run the full multi-agent pipeline for a given session ID.

    Returns:
        The final pipeline state dict. DataFrames are removed from the
        response dict before returning to make it JSON serializable.
    """
    logger.info(f"Starting agent pipeline for session {session_id[:8]}")
    
    initial_state = {
        "session_id": session_id,
        "raw_df": None,
        "clean_df": None,
        "schema": {},
        "quality_report": {},
        "audit_log": [],
        "charts": [],
        "insight_summary": "",
        "error": None,
        "current_agent": "start",
    }
    
    try:
        # Run the graph
        final_state = pipeline.invoke(initial_state)
        
        # Strip DataFrames out of the state before returning to API layer
        # as they are not JSON serializable and are cached in memory anyway
        safe_state = dict(final_state)
        safe_state.pop("raw_df", None)
        safe_state.pop("clean_df", None)
        
        return safe_state
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {type(e).__name__}")
        return {
            "session_id": session_id,
            "error": "Internal pipeline error. Please try again.",
            "current_agent": "orchestrator"
        }
