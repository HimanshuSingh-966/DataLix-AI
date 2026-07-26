import pandas as pd
import numpy as np
import gzip
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
        
        # Snapshot the pristine dataset (gzipped CSV) so reset_dataset can undo
        # any later mutations without holding a second DataFrame in memory
        original_buf = io.StringIO()
        df.to_csv(original_buf, index=False)
        original_csv_gz = gzip.compress(original_buf.getvalue().encode('utf-8'))

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
            "original_columns": len(df.columns),
            "original_csv_gz": original_csv_gz
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
    
    def calculate_statistics(
        self,
        session_id: str,
        columns: Optional[List[str]] = None,
        group_by: Optional[str] = None
    ) -> Dict:
        """Calculate statistical summary, optionally grouped by a categorical column"""
        df = self.get_dataframe(session_id)
        if group_by:
            if group_by not in df.columns:
                raise ValueError(f"Column '{group_by}' not found. Available: {', '.join(df.columns)}")
            if columns:
                numeric_cols = [c for c in columns if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
            else:
                numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            numeric_cols = [c for c in numeric_cols if c != group_by]
            if not numeric_cols:
                raise ValueError("No numeric columns to aggregate")

            grouped = df.groupby(group_by, dropna=False)[numeric_cols].agg(
                ['count', 'mean', 'median', 'min', 'max']
            )
            groups = []
            for group_value, row in grouped.head(50).iterrows():
                entry: Dict[str, Any] = {"group": str(group_value)}
                for col in numeric_cols:
                    entry[col] = {
                        "count": int(row[(col, 'count')]),
                        "mean": round(float(row[(col, 'mean')]), 4),
                        "median": round(float(row[(col, 'median')]), 4),
                        "min": float(row[(col, 'min')]),
                        "max": float(row[(col, 'max')]),
                    }
                groups.append(entry)
            return {
                "group_by": group_by,
                "group_count": int(df[group_by].nunique(dropna=False)),
                "groups": groups
            }
        return calculate_statistics(df, columns)

    FILTER_OPERATORS = ('>', '<', '==', '!=', '>=', '<=', 'contains')

    def _coerce_filter_value(self, series: pd.Series, value: str) -> Any:
        """Convert a raw string value to the column's dtype (numeric or datetime)"""
        if pd.api.types.is_numeric_dtype(series):
            return float(value)
        if pd.api.types.is_datetime64_any_dtype(series):
            return pd.to_datetime(value)
        return value

    def filter_rows(
        self,
        session_id: str,
        conditions: List[Dict[str, str]],
        combine: str = "and",
        mode: str = "view"
    ) -> Dict[str, Any]:
        """Filter rows by one or more conditions.

        mode="view" (default): returns the matching rows WITHOUT changing the
        dataset. mode="permanent": keeps only matching rows and persists.
        """
        df = self.get_dataframe(session_id)
        if not conditions:
            raise ValueError("At least one filter condition is required")

        mask = None
        described = []
        for cond in conditions:
            col = str(cond.get('column', ''))
            op = str(cond.get('operator', ''))
            raw_val = str(cond.get('value', ''))
            if col not in df.columns:
                raise ValueError(f"Column '{col}' not found. Available: {', '.join(df.columns)}")
            if op not in self.FILTER_OPERATORS:
                raise ValueError(f"Unsupported operator '{op}'. Use: {', '.join(self.FILTER_OPERATORS)}")

            if op == 'contains':
                cond_mask = df[col].astype(str).str.contains(str(raw_val), case=False, regex=False)
            else:
                try:
                    val = self._coerce_filter_value(df[col], raw_val)
                except (ValueError, TypeError):
                    raise ValueError(f"Cannot convert '{raw_val}' for column '{col}'")
                if op == '>':
                    cond_mask = df[col] > val
                elif op == '<':
                    cond_mask = df[col] < val
                elif op == '==':
                    cond_mask = df[col] == val
                elif op == '!=':
                    cond_mask = df[col] != val
                elif op == '>=':
                    cond_mask = df[col] >= val
                else:
                    cond_mask = df[col] <= val

            described.append(f"{col} {op} {raw_val}")
            mask = cond_mask if mask is None else (mask & cond_mask if combine == "and" else mask | cond_mask)

        df_filtered = df[mask]
        joiner = f" {combine.upper()} "
        description = joiner.join(described)

        if mode == "permanent":
            self.update_dataframe(session_id, pd.DataFrame(df_filtered))
            return {
                "message": f"✓ Permanently kept {len(df_filtered)} rows where {description} (removed {len(df) - len(df_filtered)} rows)",
                "mode": "permanent",
                "matching_rows": len(df_filtered),
                "removed_rows": len(df) - len(df_filtered),
                "preview": self._create_preview(pd.DataFrame(df_filtered), max_rows=100)
            }
        return {
            "message": f"Found {len(df_filtered)} of {len(df)} rows where {description} (dataset unchanged — say 'permanently' to keep only these rows)",
            "mode": "view",
            "matching_rows": len(df_filtered),
            "total_rows": len(df),
            "preview": self._create_preview(pd.DataFrame(df_filtered), max_rows=100)
        }

    def sort_data(
        self,
        session_id: str,
        column: str,
        order: str = "desc",
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Sort the dataset by a column; optionally return just the top N rows (view only)"""
        df = self.get_dataframe(session_id)
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found. Available: {', '.join(df.columns)}")
        ascending = str(order).lower() in ('asc', 'ascending')
        df_sorted = df.sort_values(column, ascending=ascending)

        if limit:
            top = df_sorted.head(int(limit))
            return {
                "message": f"Top {len(top)} rows by {column} ({'ascending' if ascending else 'descending'})",
                "rows": len(top),
                "preview": self._create_preview(pd.DataFrame(top), max_rows=min(int(limit), 100)),
                "records": json.loads(top.head(25).to_json(orient='records', date_format='iso'))
            }
        self.update_dataframe(session_id, pd.DataFrame(df_sorted))
        return {
            "message": f"✓ Dataset sorted by {column} ({'ascending' if ascending else 'descending'})",
            "preview": self._create_preview(pd.DataFrame(df_sorted), max_rows=100)
        }

    def add_column(self, session_id: str, name: str, formula: str) -> Dict[str, Any]:
        """Create a derived column from an arithmetic formula over existing columns"""
        df = self.get_dataframe(session_id)
        name = str(name).strip()
        if not name:
            raise ValueError("Column name is required")
        if name in df.columns:
            raise ValueError(f"Column '{name}' already exists")
        try:
            # df.eval only permits arithmetic/comparison over columns — no
            # attribute access or function calls, so untrusted formulas are safe
            result = df.eval(formula)
        except Exception:
            raise ValueError(
                f"Invalid formula '{formula}'. Use column names with + - * / ( ), "
                f"e.g. 'Marks / 100 * Attendance'. Available columns: {', '.join(df.columns)}"
            )
        df = df.copy()
        df[name] = result
        self.update_dataframe(session_id, df)
        return {
            "message": f"✓ Added column '{name}' = {formula}",
            "columns": len(df.columns),
            "preview": self._create_preview(df, max_rows=100)
        }

    def rename_column(self, session_id: str, old_name: str, new_name: str) -> Dict[str, Any]:
        """Rename a column"""
        df = self.get_dataframe(session_id)
        if old_name not in df.columns:
            raise ValueError(f"Column '{old_name}' not found. Available: {', '.join(df.columns)}")
        if new_name in df.columns:
            raise ValueError(f"Column '{new_name}' already exists")
        df = df.rename(columns={old_name: new_name})
        self.update_dataframe(session_id, df)
        return {
            "message": f"✓ Renamed column '{old_name}' to '{new_name}'",
            "preview": self._create_preview(df, max_rows=100)
        }

    def get_duplicates(self, session_id: str) -> Dict[str, Any]:
        """Show duplicated rows without removing them"""
        df = self.get_dataframe(session_id)
        dupes = df[df.duplicated(keep=False)]
        return {
            "message": f"Found {int(df.duplicated().sum())} duplicate rows ({len(dupes)} rows involved). Dataset unchanged — use clean_data to remove them.",
            "duplicate_rows": int(df.duplicated().sum()),
            "preview": self._create_preview(pd.DataFrame(dupes), max_rows=100) if len(dupes) else None
        }

    def reset_dataset(self, session_id: str) -> Dict[str, Any]:
        """Restore the dataset to its state at upload, undoing all mutations"""
        session = self.sessions.get(session_id)
        if session is None:
            self.get_dataframe(session_id)  # trigger restore or raise
            session = self.sessions[session_id]
        original_gz = session.get("original_csv_gz")
        if not original_gz:
            raise ValueError(
                "Original snapshot unavailable for this session (it predates this feature "
                "or was restored after a server restart). Re-upload the file to start fresh."
            )
        df = pd.read_csv(io.StringIO(gzip.decompress(original_gz).decode('utf-8')))
        self.update_dataframe(session_id, df)
        return {
            "message": f"✓ Dataset reset to original upload: {len(df)} rows, {len(df.columns)} columns",
            "rows": len(df),
            "columns": len(df.columns),
            "preview": self._create_preview(df, max_rows=100)
        }
    
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
        """Get all sessions for a user (in-memory first, then persisted ones from Supabase).

        Returns fields the frontend Session type expects (id, name, createdAt,
        updatedAt) plus a few extras (filename, rows, columns, qualityScore).
        """
        sessions = []
        seen = set()
        for session_id, session in self.sessions.items():
            if session["user_id"] == user_id:
                seen.add(session_id)
                created = session["created_at"].isoformat()
                sessions.append({
                    "id": session_id,
                    "sessionId": session_id,
                    "name": session.get("name") or session.get("filename") or "Untitled Session",
                    "filename": session.get("filename"),
                    "createdAt": created,
                    "updatedAt": session.get("updated_at", session["created_at"]).isoformat() if isinstance(session.get("updated_at"), datetime) else created,
                    "rows": len(session["dataframe"]),
                    "columns": len(session["dataframe"].columns),
                    "qualityScore": session["quality"].get("overallScore", 0)
                })
        if USE_SUPABASE_STORAGE and _supabase_admin:
            try:
                result = _supabase_admin.table("datasets") \
                    .select("session_id,file_name,created_at,updated_at,quality_score,metadata") \
                    .eq("user_id", user_id) \
                    .order("created_at", desc=True) \
                    .execute()
                for row in result.data or []:
                    sid = row["session_id"]
                    if sid in seen:
                        continue
                    meta = row.get("metadata") or {}
                    created = row.get("created_at")
                    updated = row.get("updated_at") or created
                    sessions.append({
                        "id": sid,
                        "sessionId": sid,
                        "name": row.get("file_name") or "Untitled Session",
                        "filename": row.get("file_name"),
                        "createdAt": created,
                        "updatedAt": updated,
                        "rows": meta.get("rowCount", 0),
                        "columns": meta.get("columnCount", 0),
                        "qualityScore": (row.get("quality_score") or {}).get("overallScore", 0)
                    })
            except Exception as e:
                _logger.warning("Failed to list persisted sessions: %s: %s", type(e).__name__, str(e)[:200])
        return sessions

    def rename_session(self, session_id: str, name: str) -> Dict:
        """Rename a session (in-memory + persisted)"""
        if session_id in self.sessions:
            self.sessions[session_id]["name"] = name
            self.sessions[session_id]["updated_at"] = datetime.now()
        if USE_SUPABASE_STORAGE and _supabase_admin:
            try:
                _supabase_admin.table("sessions").update({
                    "name": name,
                    "updated_at": datetime.now().isoformat(),
                }).eq("id", session_id).execute()
            except Exception as e:
                _logger.warning("Failed to rename persisted session: %s: %s", type(e).__name__, str(e)[:200])
        return {"id": session_id, "name": name}

    def get_session_messages(self, session_id: str) -> List[Dict]:
        """Return persisted chat messages for a session (empty until chat history is wired up)."""
        # Chat history persistence is planned; for now return an empty list so the
        # frontend's session-switch flow doesn't error.
        return []

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
