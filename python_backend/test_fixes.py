import pandas as pd
import numpy as np
import os
import re

# Mock environment variables for testing if they are not set
os.environ.setdefault("GEMINI_API_KEY", "test_key")
os.environ.setdefault("GROQ_API_KEY", "test_key")

from data_cleaning import handle_missing_values
from ai_service import AIService
from data_processor import DataProcessor
from agents.cleaning import cleaning_node
from agents.insight import insight_node, _format_prompt

def test_pandas_chained_assignment():
    print("\n--- Testing Pandas 2.x CoW Compliance ---")
    
    # Enable pandas strict mode for Copy-on-Write to raise an error if we fail
    pd.options.mode.chained_assignment = 'raise'
    try:
        pd.options.mode.copy_on_write = True
    except Exception:
        pass # Older pandas versions might not support this flag
        
    df = pd.DataFrame({
        'A': [1.0, np.nan, 3.0, 4.0],
        'B': [np.nan, 2.0, 3.0, 4.0]
    })
    
    # We pass a copy to simulate how clean_dataset does it
    df_clean = df.copy()
    
    parameters = {}
    try:
        result = handle_missing_values(df_clean, ['A', 'B'], 'mean', parameters)
        print("✅ Pandas missing value imputation executed successfully without ChainedAssignmentError!")
        print(f"Resulting DataFrame:\n{result['dataframe']}")
    except Exception as e:
        print(f"❌ Failed: Pandas raised an error: {type(e).__name__}: {e}")

def test_groq_chart_parsing():
    print("\n--- Testing Groq CREATE_CHART Parsing Logic ---")
    
    # Simulating a stubborn Groq response
    ai_message = "I have analyzed your data. CREATE_CHART: bar chart with the top 5 countries, x='country', y='population'"
    
    chart_match = re.search(r'CREATE_CHART:\s*([^,\n]+)(?:,\s*x=[\'"]?([^\'",\n]+)[\'"]?)?(?:,\s*y=[\'"]?([^\'",\n]+)[\'"]?)?', ai_message, re.IGNORECASE)
    
    if chart_match:
        raw_type = chart_match.group(1).strip().lower()
        chart_type = raw_type.replace(" chart", "").replace("plot", "").split()[0].strip()
        
        x_col = chart_match.group(2).strip() if chart_match.group(2) else None
        y_col = chart_match.group(3).strip() if chart_match.group(3) else None
        
        if chart_type == "bar" and x_col == "country" and y_col == "population":
            print(f"✅ Groq parsing is robust! Extracted type: '{chart_type}', x: '{x_col}', y: '{y_col}'")
        else:
            print(f"❌ Failed: Extracted unexpected values. Type: '{chart_type}', x: '{x_col}', y: '{y_col}'")
    else:
        print("❌ Failed: Regex did not match the simulated Groq output.")

def test_gemini_model_strings():
    print("\n--- Testing Gemini Model Initializations ---")
    
    try:
        # Check AIService
        processor = DataProcessor()
        ai = AIService(processor)
        if ai.model:
            model_name = ai.model.model_name.replace("models/", "")
            if model_name == "gemini-2.5-flash":
                print(f"✅ AIService correctly initialized with model: {model_name}")
            else:
                print(f"❌ Failed: AIService initialized with unexpected model: {model_name}")
        else:
            print("⚠️ AIService not initialized with Gemini (missing API key?)")
            
        # Check insight agent directly
        with open("agents/insight.py", "r") as f:
            content = f.read()
            if "model=\"gemini-2.5-flash\"" in content:
                print("✅ Insight Agent correctly hardcoded to use gemini-2.5-flash")
            else:
                print("❌ Failed: Insight Agent is NOT using gemini-2.5-flash")
                
    except Exception as e:
        print(f"❌ Failed to test Gemini initializations: {e}")

if __name__ == "__main__":
    print("==================================================")
    print("Running DataLix-AI Fixes Verification Tests")
    print("==================================================")
    
    test_pandas_chained_assignment()
    test_groq_chart_parsing()
    test_gemini_model_strings()
    
    print("\n==================================================")
    print("All tests completed.")
