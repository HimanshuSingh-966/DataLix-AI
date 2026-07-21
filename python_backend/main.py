from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from collections import defaultdict, deque
import logging
import time
import uvicorn
import os
from dotenv import load_dotenv

# Load env variables before importing local modules
load_dotenv()

from auth import get_current_user, router as auth_router
from data_processor import DataProcessor
from ai_service import AIService
from example_data import get_example_dataset, list_example_datasets

logger = logging.getLogger("datalix.main")

IS_PRODUCTION = os.getenv("NODE_ENV", "").lower() == "production"

# Hide interactive API docs and the OpenAPI schema in production
app = FastAPI(
    title="DataLix AI API",
    version="4.0.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)

# CORS middleware — wildcard origins must not be combined with credentials
ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5000,http://localhost:5173,http://localhost:3000"
    ).split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "50")) * 1024 * 1024
ALLOWED_UPLOAD_EXTENSIONS = {"csv", "xlsx", "xls", "json", "parquet"}

# ---------------------------------------------------------------------------
# Rate limiting — in-memory sliding window, per client IP.
# Buckets: (path prefix, max requests, window seconds). First match wins;
# anything unmatched falls into the global bucket.
# ---------------------------------------------------------------------------
RATE_LIMIT_BUCKETS = [
    ("/auth/", 10, 60),      # brute-force protection on signin/signup
    ("/upload", 10, 60),     # expensive: file parsing
    ("/load-example-dataset", 20, 60),
    ("/analyze", 10, 60),    # expensive: full agent pipeline
    ("/chat", 30, 60),       # expensive: LLM calls
]
GLOBAL_RATE_LIMIT = (120, 60)

_rate_hits: Dict[tuple, deque] = defaultdict(deque)
_rate_last_prune = [0.0]


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.method == "OPTIONS":  # never throttle CORS preflights
        return await call_next(request)

    ip = request.client.host if request.client else "unknown"
    path = request.url.path
    now = time.time()

    limit, window, bucket = *GLOBAL_RATE_LIMIT, "global"
    for prefix, lim, win in RATE_LIMIT_BUCKETS:
        if path.startswith(prefix):
            limit, window, bucket = lim, win, prefix
            break

    hits = _rate_hits[(ip, bucket)]
    while hits and now - hits[0] > window:
        hits.popleft()
    if len(hits) >= limit:
        retry_after = max(1, int(window - (now - hits[0])) + 1)
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please slow down."},
            headers={"Retry-After": str(retry_after)},
        )
    hits.append(now)

    # periodically drop empty deques so the map doesn't grow unbounded
    if now - _rate_last_prune[0] > 300:
        _rate_last_prune[0] = now
        for key in [k for k, v in _rate_hits.items() if not v]:
            del _rate_hits[key]

    return await call_next(request)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """422 responses must not echo submitted values (e.g. passwords)."""
    errors = [
        {"loc": e.get("loc"), "msg": e.get("msg"), "type": e.get("type")}
        for e in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


def safe_error(e: Exception, status_code: int = 400) -> HTTPException:
    """Convert an exception into an HTTPException without leaking internals.

    ValueError messages are written for users (e.g. "Column 'x' not found") and
    pass through; anything else is logged server-side and replaced with a
    generic message.
    """
    if isinstance(e, ValueError):
        return HTTPException(status_code=status_code, detail=str(e)[:300])
    logger.error("Unhandled error: %s: %s", type(e).__name__, str(e)[:300])
    return HTTPException(status_code=status_code, detail="Operation failed. Please try again.")

# Global instances - shared data processor for session consistency
data_processor = DataProcessor()
ai_service = AIService(data_processor)

# Include auth routes
app.include_router(auth_router, prefix="/auth", tags=["auth"])

# Request/Response Models
class ChatRequest(BaseModel):
    session_id: str
    message: str
    provider: Optional[str] = "auto"

class ChatResponse(BaseModel):
    message: str
    function_calls: Optional[List[str]] = None
    results: Optional[Any] = None
    data_preview: Optional[Dict] = None
    chart_data: Optional[Dict] = None
    suggested_actions: Optional[List[Dict]] = None
    quality_score: Optional[float] = None

class OperationRequest(BaseModel):
    session_id: str
    operation: str
    parameters: Optional[Dict] = None

class AnalyzeRequest(BaseModel):
    session_id: str

def require_session_owner(session_id: str, user: Dict):
    """Reject requests against sessions the authenticated user doesn't own.

    Responds 404 (not 403) so session IDs can't be probed for existence.
    """
    owner = data_processor.get_session_owner(session_id)
    if owner is not None and owner != user.get('id'):
        raise HTTPException(status_code=404, detail="Session not found")

@app.get("/")
async def root():
    return {"message": "DataLix AI API", "version": "4.0.0", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "python_version": "3.11"}

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user: Dict = Depends(get_current_user)
):
    """Upload and analyze a dataset"""
    try:
        # Get filename, default to 'unknown.csv' if None
        filename = file.filename or 'unknown.csv'

        ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
        if ext not in ALLOWED_UPLOAD_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))}"
            )

        # Read file content
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB"
            )
        
        # Process the file
        session_id, result = await data_processor.process_upload(
            content, filename, user['id']
        )
        
        return {
            "sessionId": session_id,
            "datasetInfo": result["dataset_info"],
            "quality": result["quality"],
            "preview": result["preview"],
            "issues": result["issues"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise safe_error(e)

@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: Dict = Depends(get_current_user)
):
    """Process natural language queries using AI (Groq or Gemini)"""
    require_session_owner(request.session_id, user)
    try:
        provider = request.provider or "auto"
        response = await ai_service.process_message(
            session_id=request.session_id,
            message=request.message,
            user_id=user['id'],
            provider=provider
        )
        return response
    except Exception as e:
        raise safe_error(e)

@app.post("/analyze")
async def analyze_dataset(
    request: AnalyzeRequest,
    user: Dict = Depends(get_current_user)
):
    """Run the full multi-agent analysis pipeline on a session's dataset"""
    require_session_owner(request.session_id, user)
    try:
        from agents import run_pipeline
        state = run_pipeline(request.session_id)

        if state.get("error"):
            raise HTTPException(status_code=400, detail=state["error"])

        return {
            "quality_report": state.get("quality_report", {}),
            "audit_log": state.get("audit_log", []),
            "charts": state.get("charts", []),
            "insight_summary": state.get("insight_summary", "")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise safe_error(e)

@app.get("/ai-providers")
async def get_ai_providers():
    """Get available AI providers"""
    return {
        "providers": {
            "gemini": ai_service.gemini_available,
            "groq": ai_service.groq_available
        },
        "default": "groq" if ai_service.groq_available else "gemini" if ai_service.gemini_available else None
    }

@app.post("/statistics")
async def get_statistics(
    request: OperationRequest,
    user: Dict = Depends(get_current_user)
):
    """Get statistical summary of dataset"""
    require_session_owner(request.session_id, user)
    try:
        stats = data_processor.calculate_statistics(request.session_id)
        return {"statistics": stats}
    except Exception as e:
        raise safe_error(e)

@app.post("/correlation")
async def get_correlation(
    request: OperationRequest,
    user: Dict = Depends(get_current_user)
):
    """Get correlation matrix"""
    require_session_owner(request.session_id, user)
    try:
        corr = data_processor.calculate_correlation(request.session_id)
        return {"correlation": corr}
    except Exception as e:
        raise safe_error(e)

@app.post("/visualize")
async def create_visualization(
    request: OperationRequest,
    user: Dict = Depends(get_current_user)
):
    """Create a visualization"""
    require_session_owner(request.session_id, user)
    try:
        params = request.parameters or {}
        chart = data_processor.create_visualization(
            session_id=request.session_id,
            chart_type=params.get('chart_type', 'scatter'),
            x_column=params.get('x_column', ''),
            y_column=params.get('y_column', ''),
            parameters=params
        )
        return {"chartData": chart}
    except Exception as e:
        raise safe_error(e)

@app.post("/clean")
async def clean_data(
    request: OperationRequest,
    user: Dict = Depends(get_current_user)
):
    """Clean dataset (handle missing values, outliers, duplicates)"""
    require_session_owner(request.session_id, user)
    try:
        params = request.parameters or {}
        result = data_processor.clean_data(
            session_id=request.session_id,
            parameters=params
        )
        return result
    except Exception as e:
        raise safe_error(e)

@app.post("/ml-analysis")
async def ml_analysis(
    request: OperationRequest,
    user: Dict = Depends(get_current_user)
):
    """Perform ML analysis (clustering, anomaly detection, etc.)"""
    require_session_owner(request.session_id, user)
    try:
        params = request.parameters or {}
        result = data_processor.ml_analysis(
            session_id=request.session_id,
            analysis_type=params.get('analysis_type', 'clustering'),
            parameters=params
        )
        return result
    except Exception as e:
        raise safe_error(e)

@app.post("/export")
async def export_data(
    request: OperationRequest,
    user: Dict = Depends(get_current_user)
):
    """Export dataset in various formats"""
    require_session_owner(request.session_id, user)
    try:
        params = request.parameters or {}
        file_path = data_processor.export_data(
            session_id=request.session_id,
            format=params.get('format', 'csv'),
            parameters=params
        )
        return FileResponse(
            file_path,
            media_type="application/octet-stream",
            filename=os.path.basename(file_path)
        )
    except Exception as e:
        raise safe_error(e)

@app.get("/sessions")
async def get_sessions(user: Dict = Depends(get_current_user)):
    """Get user's data sessions"""
    try:
        sessions = data_processor.get_user_sessions(user['id'])
        return sessions
    except Exception as e:
        raise safe_error(e)

@app.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: Dict = Depends(get_current_user)
):
    """Delete a data session"""
    require_session_owner(session_id, user)
    try:
        data_processor.delete_session(session_id)
        return {"message": "Session deleted successfully"}
    except Exception as e:
        raise safe_error(e)

@app.get("/user/message-limit")
async def get_message_limit(user: Dict = Depends(get_current_user)):
    """Get user's message limit (currently returning unlimited for python backend)"""
    return {
        "limit": -1,
        "current": 0,
        "remaining": -1,
        "isMaster": True
    }

@app.get("/example-datasets")
async def get_example_datasets():
    """List available example datasets"""
    return {"datasets": list_example_datasets()}

@app.post("/load-example-dataset")
async def load_example_dataset(
    dataset_id: str,
    user: Dict = Depends(get_current_user)
):
    """Load an example dataset"""
    try:
        csv_data = get_example_dataset(dataset_id)
        
        datasets = list_example_datasets()
        dataset_info = next((d for d in datasets if d['id'] == dataset_id), None)
        if not dataset_info:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        filename = f"{dataset_id}_example.csv"
        
        session_id, result = await data_processor.process_upload(
            csv_data, filename, user['id']
        )
        
        return {
            "sessionId": session_id,
            "datasetInfo": result["dataset_info"],
            "quality": result["quality"],
            "preview": result["preview"],
            "issues": result["issues"],
            "exampleDatasetName": dataset_info['name']
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise safe_error(e, 404)
    except Exception as e:
        raise safe_error(e)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=not IS_PRODUCTION,
        proxy_headers=True,  # trust X-Forwarded-For from the Node/nginx proxy
    )
