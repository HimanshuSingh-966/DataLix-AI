import pandas as pd
import numpy as np
import json
import io
import uuid
import os
import logging
import tempfile
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

_logger = logging.getLogger("datalix.processor")

from data_quality import analyze_data_quality
from statistics_module import calculate_statistics, calculate_correlation
from ml_analysis import perform_ml_analysis
from visualizations import create_visualization as create_viz
from data_cleaning import clean_dataset, handle_missing_values, detect_and_handle_outliers, remove_duplicates

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
USE_SUPABASE_STORAGE = bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)

_supabase_admin = None
if USE_SUPABASE_STORAGE:
    try:
        from supabase import create_client
        _supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        _logger.info("Supabase dataset persistence enabled")
    except Exception as e:
        _logger.warning("Supabase init failed, using in-memory only")
        USE_SUPABASE_STORAGE = False

# ─── DataFrame Cache ───────────────────────────────────────────────
# In-memory cache keyed by session_id, with 2-hour TTL eviction.
# Prevents re-parsing large files on every API call.
_df_cache: Dict[str, Dict] = {}
# Structure: { session_id: { "df": DataFrame, "created_at": datetime } }

CACHE_MAX_AGE_HOURS = 2

def get_cached_df(session_id: str) -> Optional[pd.DataFrame]:
    """Returns DataFrame if exists and not expired, else None."""
    entry = _df_cache.get(session_id)
    if entry is None:
        return None
    age = (datetime.now() - entry["created_at"]).total_seconds() / 3600
    if age > CACHE_MAX_AGE_HOURS:
        _logger.info(f"Cache expired for session {session_id[:8]}")
        del _df_cache[session_id]
        return None
    _logger.info(f"Cache hit for session {session_id[:8]}")
    return entry["df"]

def cache_df(session_id: str, df: pd.DataFrame) -> None:
    """Stores DataFrame with timestamp."""
    _df_cache[session_id] = {"df": df, "created_at": datetime.now()}
    _logger.info(f"Cached DataFrame for session {session_id[:8]} ({len(df)} rows)")

def evict_expired_sessions(max_age_hours: int = CACHE_MAX_AGE_HOURS) -> None:
    """Removes sessions older than max_age_hours. Call at start of each request."""
    now = datetime.now()
    expired = [
        sid for sid, entry in _df_cache.items()
        if (now - entry["created_at"]).total_seconds() / 3600 > max_age_hours
    ]
    for sid in expired:
        del _df_cache[sid]
    if expired:
        _logger.info(f"Evicted {len(expired)} expired cache entries")

def sanitize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Sanitize column names: strip whitespace, replace special chars."""
    new_cols = {}
    for col in df.columns:
        clean = str(col).strip()
        # Replace characters that break prompts/queries
        clean = clean.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        # Collapse multiple spaces
        while '  ' in clean:
            clean = clean.replace('  ', ' ')
        new_cols[col] = clean
    if any(old != new for old, new in new_cols.items()):
        df = df.rename(columns=new_cols)
        _logger.info(f"Sanitized column names: {[old for old, new in new_cols.items() if old != new]}")
    return df


class DataProcessor:
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def _persist_dataset(self, session_id: str, user_id: str, df: pd.DataFrame,
                         quality: Dict, preview: Dict, metadata: Dict):
        if not USE_SUPABASE_STORAGE or not _supabase_admin:
            return
        try:
            csv_buf = io.StringIO()
            df.to_csv(csv_buf, index=False)
            csv_data = csv_buf.getvalue()

            # datasets.session_id has a FK to sessions(id) — the parent row must exist first
            _supabase_admin.table("sessions").upsert({
                "id": session_id,
                "user_id": user_id,
                "name": metadata.get("fileName"),
            }, on_conflict="id").execute()

            _supabase_admin.table("datasets").upsert({
                "session_id": session_id,
                "user_id": user_id,
                "file_name": metadata.get("fileName"),
                "data_csv": csv_data,
                "data_preview": json.loads(json.dumps(preview, default=str)),
                "quality_score": json.loads(json.dumps(quality, default=str)),
                "metadata": json.loads(json.dumps(metadata, default=str)),
            }, on_conflict="session_id").execute()
        except Exception as e:
            _logger.error("Failed to persist dataset: %s: %s", type(e).__name__, str(e)[:200])

    def _restore_dataset(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not USE_SUPABASE_STORAGE or not _supabase_admin:
            return None
        try:
            result = _supabase_admin.table("datasets").select("*").eq("session_id", session_id).single().execute()
            if not result.data:
                return None
            row = result.data
            csv_data = row.get("data_csv")
            if not csv_data:
                return None
            df = pd.read_csv(io.StringIO(csv_data))
            return {
                "session_id": session_id,
                "user_id": row.get("user_id", ""),
                "dataframe": df,
                "filename": row.get("file_name"),
                "created_at": datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now(),
                "quality": row.get("quality_score", {}),
                "preview": row.get("data_preview", {}),
                "original_rows": (row.get("metadata") or {}).get("rowCount", len(df)),
                "original_columns": (row.get("metadata") or {}).get("columnCount", len(df.columns)),
            }
        except Exception as e:
            _logger.warning("Failed to restore dataset %s", session_id[:8])
            return None
    
    async def process_upload(
        self, 
        content: bytes, 
        filename: str, 
        user_id: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Process uploaded file and create a new session"""
        
        # Parse file based on extension
        ext = filename.lower().split('.')[-1]
        
        try:
            if ext == 'csv':
                df = pd.read_csv(io.BytesIO(content))
            elif ext in ['xlsx', 'xls']:
                df = pd.read_excel(io.BytesIO(content))
            elif ext == 'json':
                df = pd.read_json(io.BytesIO(content))
            elif ext == 'parquet':
                df = pd.read_parquet(io.BytesIO(content))
            else:
                raise ValueError(f"Unsupported file format: {ext}")
        except Exception as e:
            raise ValueError(f"Failed to parse file: unsupported or invalid format")

        # Cap dataset dimensions — compressed formats (xlsx/parquet) can expand
        # far beyond the raw upload size limit
        max_rows = int(os.getenv("MAX_DATASET_ROWS", "1000000"))
        max_cols = int(os.getenv("MAX_DATASET_COLUMNS", "500"))
        if len(df) > max_rows:
            raise ValueError(f"Dataset too large: {len(df)} rows (maximum {max_rows})")
        if len(df.columns) > max_cols:
            raise ValueError(f"Dataset has too many columns: {len(df.columns)} (maximum {max_cols})")
        if len(df) == 0 or len(df.columns) == 0:
            raise ValueError("Dataset is empty")

        # Sanitize column names
        df = sanitize_column_names(df)
        
        # Create session
        session_id = str(uuid.uuid4())
        
        # Analyze data quality
        quality_analysis = analyze_data_quality(df)
        
        # Store session with original dimensions first
        self.sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "dataframe": df,
            "filename": filename,
            "created_at": datetime.now(),
            "quality": quality_analysis,
            "preview": {},
            "original_rows": len(df),
            "original_columns": len(df.columns)
        }
        
        # Create preview with session_id to get original dimensions
        preview = self._create_preview(df, filename, session_id=session_id)
        self.sessions[session_id]["preview"] = preview

        metadata = {
            "fileName": filename,
            "rowCount": len(df),
            "columnCount": len(df.columns),
            "uploadedAt": datetime.now().isoformat(),
        }
        self._persist_dataset(session_id, user_id, df, quality_analysis, preview, metadata)

        # Cache the DataFrame
        cache_df(session_id, df)

        # Prepare response
        result = {
            "dataset_info": {
                "rows": len(df),
                "columns": len(df.columns),
                "sizeMb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
                "columnNames": df.columns.tolist(),
                "columnTypes": df.dtypes.astype(str).to_dict()
            },
            "quality": quality_analysis,
            "preview": preview,
            "issues": quality_analysis["issues"]
        }
        
        return session_id, result
    
    def _create_preview(self, df: pd.DataFrame, filename: str = None, max_rows: int = 100, session_id: str = None) -> Dict:
        """Create a data preview"""
        preview_df = df.head(max_rows)
        
        columns_info = []
        for col in df.columns:
            null_count = df[col].isnull().sum()
            unique_count = df[col].nunique()
            sample_values = df[col].dropna().unique()[:5].tolist()
            
            columns_info.append({
                "name": col,
                "type": str(df[col].dtype),
                "nullCount": int(null_count),
                "uniqueCount": int(unique_count),
                "sampleValues": sample_values
            })
        
        # Convert DataFrame to records, handling NaN values
        rows = preview_df.replace({np.nan: None}).to_dict('records')
        
        # Get original dimensions if session exists
        original_rows = len(df)
        original_columns = len(df.columns)
        
        if session_id and session_id in self.sessions:
            original_rows = self.sessions[session_id].get("original_rows", len(df))
            original_columns = self.sessions[session_id].get("original_columns", len(df.columns))
        
        return {
            "columns": columns_info,
            "rows": rows,
            "totalRows": len(df),
            "totalColumns": len(df.columns),
            "originalRows": original_rows,
            "originalColumns": original_columns,
            "fileName": filename
        }
    
    def get_dataframe(self, session_id: str) -> pd.DataFrame:
        """Get DataFrame for a session, restoring from DB if not in memory"""
        # Evict expired cache entries on each request
        evict_expired_sessions()

        if session_id not in self.sessions:
            # Try the DataFrame cache first
            cached = get_cached_df(session_id)
            if cached is not None:
                # Restore a minimal session entry from cache
                self.sessions[session_id] = {
                    "session_id": session_id,
                    "user_id": "",
                    "dataframe": cached,
                    "filename": None,
                    "created_at": datetime.now(),
                    "quality": {},
                    "preview": {},
                    "original_rows": len(cached),
                    "original_columns": len(cached.columns),
                }
                return cached

            # Fall back to Supabase persistence
            restored = self._restore_dataset(session_id)
            if restored:
                self.sessions[session_id] = restored
                # Re-cache it
                cache_df(session_id, restored["dataframe"])
            else:
                raise ValueError("Session not found")
        return self.sessions[session_id]["dataframe"]
    
    def update_dataframe(self, session_id: str, df: pd.DataFrame):
        """Update DataFrame for a session"""
        if session_id not in self.sessions:
            restored = self._restore_dataset(session_id)
            if restored:
                self.sessions[session_id] = restored
            else:
                raise ValueError("Session not found")

        if "original_rows" not in self.sessions[session_id]:
            self.sessions[session_id]["original_rows"] = len(df)
            self.sessions[session_id]["original_columns"] = len(df.columns)

        self.sessions[session_id]["dataframe"] = df
        self.sessions[session_id]["preview"] = self._create_preview(
            df,
            self.sessions[session_id].get("filename"),
            session_id=session_id
        )

        quality = analyze_data_quality(df)
        self.sessions[session_id]["quality"] = quality

        self._persist_dataset(
            session_id,
            self.sessions[session_id].get("user_id", ""),
            df,
            quality,
            self.sessions[session_id]["preview"],
            {
                "fileName": self.sessions[session_id].get("filename"),
                "rowCount": len(df),
                "columnCount": len(df.columns),
                "uploadedAt": self.sessions[session_id].get("created_at", datetime.now()).isoformat() if isinstance(self.sessions[session_id].get("created_at"), datetime) else str(self.sessions[session_id].get("created_at", "")),
            }
        )
    
    def calculate_statistics(self, session_id: str, columns: Optional[List[str]] = None) -> Dict:
        """Calculate statistical summary"""
        df = self.get_dataframe(session_id)
        return calculate_statistics(df, columns)
    
    def calculate_correlation(self, session_id: str, columns: Optional[List[str]] = None) -> Dict:
        """Calculate correlation matrix"""
        df = self.get_dataframe(session_id)
        return calculate_correlation(df, columns)
    
    def detect_missing_values(self, session_id: str) -> Dict:
        """Detect and return columns with missing values"""
        df = self.get_dataframe(session_id)
        
        missing_info = []
        total_rows = len(df)
        
        for col in df.columns:
            missing_count = df[col].isnull().sum()
            if missing_count > 0:
                missing_percentage = (missing_count / total_rows) * 100
                missing_info.append({
                    "column": col,
                    "missing_count": int(missing_count),
                    "missing_percentage": round(missing_percentage, 2),
                    "data_type": str(df[col].dtype)
                })
        
        return {
            "total_rows": total_rows,
            "columns_with_missing": len(missing_info),
            "missing_data": missing_info
        }
    
    def create_visualization(
        self,
        session_id: str,
        chart_type: str,
        x_column: Optional[str] = None,
        y_column: Optional[str] = None,
        parameters: Optional[Dict] = None
    ) -> Dict:
        """Create a Plotly visualization"""
        df = self.get_dataframe(session_id)
        return create_viz(df, chart_type, x_column, y_column, parameters or {})
    
    def clean_data(self, session_id: str, parameters: Dict) -> Dict:
        """Clean dataset"""
        df = self.get_dataframe(session_id)
        result = clean_dataset(df, parameters)
        
        # Update the dataframe
        self.update_dataframe(session_id, result["dataframe"])
        
        return {
            "message": result["message"],
            "changes": result["changes"],
            "preview": self.sessions[session_id]["preview"],
            "quality": self.sessions[session_id]["quality"]
        }
    
    def ml_analysis(
        self,
        session_id: str,
        analysis_type: str,
        parameters: Optional[Dict] = None
    ) -> Dict:
        """Perform ML analysis"""
        df = self.get_dataframe(session_id)
        return perform_ml_analysis(df, analysis_type, parameters or {})
    
    def export_data(
        self,
        session_id: str,
        format: str = 'csv',
        parameters: Optional[Dict] = None
    ) -> str:
        """Export dataset to file"""
        df = self.get_dataframe(session_id)
        params = parameters or {}
        
        # Create export directory
        export_dir = os.path.join(tempfile.gettempdir(), 'datalix_exports')
        os.makedirs(export_dir, exist_ok=True)
        
        filename = params.get('filename', f'export_{session_id[:8]}')
        filename = os.path.basename(filename).replace(os.sep, '_')

        if format == 'csv':
            filepath = os.path.join(export_dir, f'{filename}.csv')
            df.to_csv(filepath, index=False, encoding=params.get('encoding', 'utf-8'))
        elif format == 'excel':
            filepath = os.path.join(export_dir, f'{filename}.xlsx')
            df.to_excel(filepath, index=False)
        elif format == 'json':
            filepath = os.path.join(export_dir, f'{filename}.json')
            df.to_json(filepath, orient='records', indent=2)
        elif format == 'parquet':
            filepath = os.path.join(export_dir, f'{filename}.parquet')
            df.to_parquet(filepath, index=False)
        else:
            raise ValueError(f"Unsupported export format: {format}")

        return filepath
    
    def get_session_owner(self, session_id: str) -> Optional[str]:
        """Return the user_id that owns a session, or None if unknown.

        Checks the in-memory session first; falls back to the persisted
        datasets table (cache-restored sessions may have an empty user_id).
        """
        session = self.sessions.get(session_id)
        if session and session.get("user_id"):
            return session["user_id"]
        if USE_SUPABASE_STORAGE and _supabase_admin:
            try:
                result = _supabase_admin.table("datasets") \
                    .select("user_id") \
                    .eq("session_id", session_id) \
                    .limit(1).execute()
                if result.data:
                    return result.data[0].get("user_id")
            except Exception as e:
                _logger.warning("Failed to look up session owner: %s", type(e).__name__)
        return None

    def get_user_sessions(self, user_id: str) -> List[Dict]:
        """Get all sessions for a user (in-memory first, then persisted ones from Supabase)"""
        sessions = []
        seen = set()
        for session_id, session in self.sessions.items():
            if session["user_id"] == user_id:
                seen.add(session_id)
                sessions.append({
                    "sessionId": session_id,
                    "filename": session.get("filename"),
                    "createdAt": session["created_at"].isoformat(),
                    "rows": len(session["dataframe"]),
                    "columns": len(session["dataframe"].columns),
                    "qualityScore": session["quality"]["overallScore"]
                })
        if USE_SUPABASE_STORAGE and _supabase_admin:
            try:
                result = _supabase_admin.table("datasets") \
                    .select("session_id,file_name,created_at,quality_score,metadata") \
                    .eq("user_id", user_id) \
                    .order("created_at", desc=True) \
                    .execute()
                for row in result.data or []:
                    sid = row["session_id"]
                    if sid in seen:
                        continue
                    meta = row.get("metadata") or {}
                    sessions.append({
                        "sessionId": sid,
                        "filename": row.get("file_name"),
                        "createdAt": row.get("created_at"),
                        "rows": meta.get("rowCount", 0),
                        "columns": meta.get("columnCount", 0),
                        "qualityScore": (row.get("quality_score") or {}).get("overallScore", 0)
                    })
            except Exception as e:
                _logger.warning("Failed to list persisted sessions: %s: %s", type(e).__name__, str(e)[:200])
        return sessions

    def delete_session(self, session_id: str):
        """Delete a session (in-memory and persisted copy)"""
        if session_id in self.sessions:
            del self.sessions[session_id]
        if USE_SUPABASE_STORAGE and _supabase_admin:
            try:
                # deleting the sessions row cascades to datasets (ON DELETE CASCADE)
                _supabase_admin.table("sessions").delete().eq("id", session_id).execute()
            except Exception as e:
                _logger.warning("Failed to delete persisted session: %s: %s", type(e).__name__, str(e)[:200])
