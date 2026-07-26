import os
import sys
import pandas as pd
import numpy as np
import traceback
import asyncio

# Setup mock environment to prevent external API calls from failing tests
os.environ.setdefault("GEMINI_API_KEY", "dummy_gemini_key")
os.environ.setdefault("GROQ_API_KEY", "dummy_groq_key")
os.environ.setdefault("DISABLE_LLM_INSIGHTS", "true")  # Prevent actual LLM calls

try:
    from dotenv import load_dotenv
    load_dotenv()  # Ensure .env is loaded so real Supabase is used
except ImportError:
    pass

# Import all modules
try:
    from data_cleaning import (
        clean_dataset, handle_missing_values, detect_and_handle_outliers,
        remove_duplicates, normalize_data
    )
    from data_processor import DataProcessor
    from data_quality import analyze_data_quality
    from ml_analysis import perform_ml_analysis
    from statistics_module import calculate_statistics, calculate_correlation
    from visualizations import create_visualization
    from ai_service import AIService
    
    # Import agents
    from agents.cleaning import cleaning_node
    from agents.visualization import visualization_node
    from agents.insight import insight_node
    
    IMPORTS_SUCCESSFUL = True
except ImportError as e:
    print(f"❌ Failed to import modules: {e}")
    IMPORTS_SUCCESSFUL = False

def create_dummy_dataframe():
    """Create a DataFrame with various data types, missing values, and outliers for testing."""
    return pd.DataFrame({
        'numeric_col1': [1.0, 2.0, np.nan, 4.0, 100.0, 2.0],  # Has nan, outlier, duplicate
        'numeric_col2': [10, 20, 30, 40, 50, 20],
        'categorical_col': ['A', 'B', 'A', 'C', np.nan, 'B'],
        'datetime_col': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05', '2023-01-02'])
    })

def run_test(test_name, test_func):
    """Wrapper to run a test and print PASS/FAIL."""
    print(f"Testing {test_name}... ", end="")
    try:
        test_func()
        print("✅ PASS")
        return True
    except Exception as e:
        print("❌ FAIL")
        print(f"   Error: {type(e).__name__}: {e}")
        traceback.print_exc(limit=1, file=sys.stdout)
        return False

# --- Test Functions ---

def test_data_quality():
    df = create_dummy_dataframe()
    result = analyze_data_quality(df)
    assert 'overallScore' in result
    assert 'issues' in result

def test_statistics_module():
    df = create_dummy_dataframe()
    stats = calculate_statistics(df, ['numeric_col1', 'numeric_col2'])
    assert 'statistics' in stats
    corr = calculate_correlation(df, ['numeric_col1', 'numeric_col2'])
    assert 'matrix' in corr
    
    from statistics_module import describe_distribution
    dist = describe_distribution(df, 'numeric_col1')
    assert 'type' in dist

def test_visualizations():
    df = create_dummy_dataframe()
    # Test a few chart types
    create_visualization(df, 'histogram', x_column='numeric_col2')
    create_visualization(df, 'scatter', x_column='numeric_col1', y_column='numeric_col2')
    create_visualization(df, 'bar', x_column='categorical_col', y_column='numeric_col2')

def test_ml_analysis():
    df = create_dummy_dataframe()
    # Clustering
    res_cluster = perform_ml_analysis(df, 'clustering', {'targetColumn': 'numeric_col2', 'algorithm': 'kmeans', 'n_clusters': 2})
    assert 'analysisType' in res_cluster
    
    # Feature Importance (which is implemented)
    res_fi = perform_ml_analysis(df, 'feature_importance', {'target_column': 'numeric_col2'})
    assert 'analysisType' in res_fi

def test_data_cleaning_functions():
    df = create_dummy_dataframe()
    
    # Test Missing Values
    res_missing = handle_missing_values(df, ['numeric_col1'], 'mean', {})
    assert res_missing['dataframe']['numeric_col1'].isnull().sum() == 0
    
    # Test Outliers
    res_outliers = detect_and_handle_outliers(df, ['numeric_col1'], 'iqr', {'outlierAction': 'remove'})
    assert len(res_outliers['dataframe']) < len(df)
    
    # Test Duplicates
    res_dup = remove_duplicates(df)
    assert len(res_dup['dataframe']) < len(df)
    
    # Test Normalization
    res_norm = normalize_data(df, ['numeric_col2'], 'minmax')
    assert res_norm['dataframe']['numeric_col2'].max() <= 1.0

def test_data_cleaning_main_wrapper():
    df = create_dummy_dataframe()
    params = {
        'handleMissing': True, 'missingMethod': 'mean',
        'removeDuplicates': True,
        'handleOutliers': True, 'outlierMethod': 'iqr'
    }
    result = clean_dataset(df, params)
    assert 'dataframe' in result

def test_data_processor():
    processor = DataProcessor()
    session_id = "test_session"
    df = create_dummy_dataframe()
    
    processor.sessions[session_id] = {
        "session_id": session_id,
        "user_id": "test_user",
        "created_at": pd.Timestamp.now()
    }
    
    processor.update_dataframe(session_id, df)
    retrieved_df = processor.get_dataframe(session_id)
    assert len(retrieved_df) == len(df)
    
    processor.calculate_statistics(session_id)
    processor.detect_missing_values(session_id)
    processor.create_visualization(session_id, 'histogram', 'numeric_col2')

def test_ai_service():
    processor = DataProcessor()
    ai = AIService(processor)
    
    session_id = "test_session"
    processor.sessions[session_id] = {
        "session_id": session_id,
        "user_id": "test_user",
        "created_at": pd.Timestamp.now()
    }
    processor.update_dataframe(session_id, create_dummy_dataframe())
    
    # Test suggestion generation
    suggestions = ai._generate_suggestions(session_id, [])
    assert isinstance(suggestions, list)
    
    # Async test wrapper for process_message
    async def run_async_test():
        # Using "auto" which will fallback gracefully due to missing real keys
        res = await ai.process_message(session_id, "test message", "user1")
        assert 'message' in res
    
    asyncio.run(run_async_test())

def test_langgraph_agents():
    df = create_dummy_dataframe()
    schema = {
        "numeric_col1": {"dtype": "numeric"},
        "categorical_col": {"dtype": "categorical", "unique_count": 3}
    }
    quality_report = analyze_data_quality(df)
    
    state = {
        "raw_df": df,
        "schema": schema,
        "quality_report": quality_report
    }
    
    # Test Cleaning Agent
    state = cleaning_node(state)
    assert "clean_df" in state
    assert "audit_log" in state
    
    # Test Visualization Agent
    state = visualization_node(state)
    assert "charts" in state
    
    # Test Insight Agent
    state = insight_node(state)
    assert "insight_summary" in state

def test_auth_routes():
    from fastapi.testclient import TestClient
    from main import app
    import uuid
    
    client = TestClient(app)
    suffix = uuid.uuid4().hex[:8]
    unique_email = f"test_{suffix}@example.com"

    # Test Signup (username must be unique too — profiles.username has a UNIQUE constraint)
    res_signup = client.post("/auth/signup", json={"email": unique_email, "password": "StrongPassword123!@#", "username": f"testuser_{suffix}"})
    
    # Enforce strict validation - test MUST fail if API fails
    assert res_signup.status_code == 200, f"Signup failed: {res_signup.text}"
    token = res_signup.json().get("access_token")
    assert token is not None
    
    # Test Signin
    res_signin = client.post("/auth/signin", json={"email": unique_email, "password": "StrongPassword123!@#"})
    assert res_signin.status_code == 200, f"Signin failed: {res_signin.text}"
    
    # Test Verify
    headers = {"Authorization": f"Bearer {token}"}
    res_verify = client.get("/auth/verify", headers=headers)
    assert res_verify.status_code == 200, f"Verify failed: {res_verify.text}"
    assert res_verify.json()["email"] == unique_email

def test_main_api_endpoints():
    from fastapi.testclient import TestClient
    from main import app
    import io
    import uuid
    
    client = TestClient(app)
    
    # Create test user and get token
    suffix = uuid.uuid4().hex[:8]
    unique_email = f"testapi_{suffix}@example.com"
    res_signup = client.post("/auth/signup", json={"email": unique_email, "password": "StrongPassword123!@#", "username": f"apiuser_{suffix}"})
    
    # Enforce strict validation
    assert res_signup.status_code == 200, f"Signup failed: {res_signup.text}"
        
    token = res_signup.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Health Route
    res_health = client.get("/health")
    assert res_health.status_code == 200
    
    # 2. Upload Route
    csv_content = b"col1,col2\n1,2\n3,4\n5,6\n7,8"  # Ensure >= 3 rows for KMeans
    files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
    res_upload = client.post("/upload", headers=headers, files=files)
    assert res_upload.status_code == 200, f"Upload failed: {res_upload.text}"
    
    session_id = res_upload.json().get("sessionId")
    assert session_id is not None
    
    # 3. Statistics Route
    res_stats = client.post("/statistics", headers=headers, json={"session_id": session_id, "operation": "statistics"})
    assert res_stats.status_code == 200, f"Stats failed: {res_stats.text}"
    
    # 4. Correlation Route
    res_corr = client.post("/correlation", headers=headers, json={"session_id": session_id, "operation": "correlation"})
    assert res_corr.status_code == 200, f"Corr failed: {res_corr.text}"
    
    # 5. ML Analysis Route
    res_ml = client.post("/ml-analysis", headers=headers, json={"session_id": session_id, "operation": "ml_analysis", "parameters": {"analysis_type": "clustering"}})
    assert res_ml.status_code == 200, f"ML Analysis failed: {res_ml.text}"
    
    # 6. User Sessions Route
    res_sessions = client.get("/sessions", headers=headers)
    assert res_sessions.status_code == 200, f"Get Sessions failed: {res_sessions.text}"

def run_all_tests():
    if not IMPORTS_SUCCESSFUL:
        print("Cannot run tests due to import errors.")
        return
        
    print("==================================================")
    print("   DataLix-AI Comprehensive Python Test Suite")
    print("==================================================")
    
    tests = [
        ("Data Quality Module", test_data_quality),
        ("Statistics Module", test_statistics_module),
        ("Visualizations Module", test_visualizations),
        ("Machine Learning Module", test_ml_analysis),
        ("Data Cleaning Sub-functions", test_data_cleaning_functions),
        ("Data Cleaning Main Wrapper", test_data_cleaning_main_wrapper),
        ("Data Processor Class", test_data_processor),
        ("AI Service Configuration", test_ai_service),
        ("LangGraph Agents (Cleaning/Viz/Insight)", test_langgraph_agents),
        ("Authentication Routes (FastAPI)", test_auth_routes),
        ("Main API Endpoints (FastAPI)", test_main_api_endpoints),
    ]
    
    passed = 0
    for name, func in tests:
        if run_test(name, func):
            passed += 1
            
    print("==================================================")
    print(f"Test Summary: {passed}/{len(tests)} Tests Passed")
    if passed == len(tests):
        print("🎉 EVERYTHING IS WORKING CORRECTLY!")
    else:
        print("⚠️ SOME TESTS FAILED. CHECK THE LOGS ABOVE.")
    print("==================================================")

if __name__ == "__main__":
    run_all_tests()
