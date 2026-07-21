from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict
import os
import uuid
import secrets
import hashlib
import time
import logging
from passlib.context import CryptContext

router = APIRouter()

logger = logging.getLogger("datalix.auth")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

FALLBACK_USERS: Dict[str, Dict] = {}
FALLBACK_SESSIONS: Dict[str, Dict] = {}
SESSION_TTL = 86400

supabase_url = os.getenv("SUPABASE_URL", "")
supabase_key = os.getenv("SUPABASE_ANON_KEY", "")
supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

USE_SUPABASE = bool(supabase_url and supabase_key and supabase_service_key)

if USE_SUPABASE:
    try:
        from supabase import create_client, Client
        supabase: Optional[Client] = create_client(
            supabase_url=supabase_url,
            supabase_key=supabase_key
        )
        supabase_admin: Optional[Client] = create_client(
            supabase_url=supabase_url,
            supabase_key=supabase_service_key
        )
        logger.info("Supabase authentication enabled")
    except Exception as e:
        logger.error(f"Supabase initialization failed: {e}")
        raise RuntimeError("Supabase initialization failed") from e
else:
    logger.warning("Supabase not configured. Using fallback in-memory authentication.")


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    username: str = Field(min_length=2, max_length=32, pattern=r'^[a-zA-Z0-9_.-]+$')

class SignInRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    user: Dict
    session: Dict
    access_token: str


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


@router.post("/signup", response_model=AuthResponse)
async def signup(request: SignUpRequest):
    if USE_SUPABASE and supabase:
        try:
            response = supabase.auth.sign_up({
                "email": request.email,
                "password": request.password,
                "options": {
                    "data": {
                        "username": request.username
                    }
                }
            })

            if response.user is None:
                raise HTTPException(status_code=400, detail="Signup failed - user not created")

            logger.info("User created via Supabase Auth")

            if response.session is None:
                access_token = secrets.token_urlsafe(32)
                FALLBACK_SESSIONS[access_token] = {"user_id": f"supabase:{response.user.id}", "created_at": time.time()}
                FALLBACK_USERS[f"supabase:{response.user.id}"] = {
                    "id": response.user.id,
                    "email": response.user.email,
                    "username": request.username
                }
                return {
                    "user": {
                        "id": response.user.id,
                        "email": response.user.email,
                        "username": request.username
                    },
                    "session": {
                        "access_token": access_token,
                        "refresh_token": access_token
                    },
                    "access_token": access_token
                }

            return {
                "user": {
                    "id": response.user.id,
                    "email": response.user.email,
                    "username": request.username
                },
                "session": {
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token
                },
                "access_token": response.session.access_token
            }
        except HTTPException:
            raise
        except Exception as e:
            error_msg = getattr(e, 'message', str(e))
            logger.error("Supabase signup failed: %s - %s", type(e).__name__, error_msg)
            indicator = str(error_msg).lower()
            # Map known cases to safe messages; never echo raw provider errors
            if "already" in indicator and ("registered" in indicator or "exists" in indicator):
                raise HTTPException(status_code=400, detail="An account with this email already exists")
            if "password" in indicator:
                raise HTTPException(status_code=400, detail="Password does not meet requirements")
            raise HTTPException(status_code=400, detail="Signup failed. Please try again later.")
    else:
        if request.email in FALLBACK_USERS:
            raise HTTPException(status_code=400, detail="User already exists")

        user_id = str(uuid.uuid4())
        access_token = secrets.token_urlsafe(32)

        FALLBACK_USERS[request.email] = {
            "id": user_id,
            "email": request.email,
            "username": request.username,
            "password": hash_password(request.password)
        }

        FALLBACK_SESSIONS[access_token] = {"user_id": user_id, "created_at": time.time()}

        return {
            "user": {
                "id": user_id,
                "email": request.email,
                "username": request.username
            },
            "session": {
                "access_token": access_token,
                "refresh_token": access_token
            },
            "access_token": access_token
        }


@router.post("/signin", response_model=AuthResponse)
async def signin(request: SignInRequest):
  if USE_SUPABASE and supabase:
    try:
      response = supabase.auth.sign_in_with_password({
        "email": request.email,
        "password": request.password
      })

      if response.user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

      if response.session is None:
        raise HTTPException(status_code=401, detail="Session not created")

      username = response.user.user_metadata.get('username', response.user.email.split('@')[0] if response.user.email else 'user')

      return {
        "user": {
          "id": response.user.id,
          "email": response.user.email,
          "username": username
        },
        "session": {
          "access_token": response.session.access_token,
          "refresh_token": response.session.refresh_token
        },
        "access_token": response.session.access_token
      }
    except HTTPException:
      raise
    except Exception as e:
      error_type = type(e).__name__.lower()
      error_attr = getattr(e, 'message', '') or getattr(e, 'code', '') or ''
      error_indicator = f"{error_type} {error_attr}".lower()
      if "email" in error_indicator and "confirm" in error_indicator:
        raise HTTPException(
          status_code=401,
          detail="Email not confirmed. Please check your email inbox and click the confirmation link before signing in."
        )
      raise HTTPException(status_code=401, detail="Invalid credentials")
  else:
    if request.email not in FALLBACK_USERS:
      raise HTTPException(status_code=401, detail="Invalid credentials")

    user = FALLBACK_USERS[request.email]
    if not verify_password(request.password, user["password"]):
      raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = secrets.token_urlsafe(32)
    FALLBACK_SESSIONS[access_token] = {"user_id": user["id"], "created_at": time.time()}

    return {
      "user": {
        "id": user["id"],
        "email": user["email"],
        "username": user["username"]
      },
      "session": {
        "access_token": access_token,
        "refresh_token": access_token
      },
      "access_token": access_token
    }


async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.split(" ")[1]

    if token in FALLBACK_SESSIONS:
        session_data = FALLBACK_SESSIONS[token]
        if time.time() - session_data["created_at"] > SESSION_TTL:
            del FALLBACK_SESSIONS[token]
            raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
        user_key = session_data["user_id"]

        if user_key.startswith("supabase:") and user_key in FALLBACK_USERS:
            user = FALLBACK_USERS[user_key]
            return {
                "id": user["id"],
                "email": user["email"],
                "username": user["username"],
                "isMaster": user.get("isMaster", 0)
            }

        user = next((u for u in FALLBACK_USERS.values() if u["id"] == user_key), None)

        if user:
            return {
                "id": user["id"],
                "email": user["email"],
                "username": user["username"],
                "isMaster": user.get("isMaster", 0)
            }

    if USE_SUPABASE and supabase_admin:
        try:
            user_response = supabase_admin.auth.get_user(token)

            if not user_response or not user_response.user:
                raise HTTPException(status_code=401, detail="Invalid token")

            username = user_response.user.user_metadata.get('username', user_response.user.email.split('@')[0] if user_response.user.email else 'user')

            is_master = 0
            try:
                user_data = supabase_admin.table("profiles").select("is_master").eq("id", user_response.user.id).single().execute()
                if isinstance(user_data.data, dict):
                    is_master = user_data.data.get("is_master", 0)
            except Exception:
                pass

            return {
                "id": user_response.user.id,
                "email": user_response.user.email,
                "username": username,
                "isMaster": is_master
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Auth verification failed: %s", type(e).__name__)
            raise HTTPException(status_code=401, detail="Authentication failed")

    raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/verify")
async def verify_token(user: Dict = Depends(get_current_user)):
    return user


@router.post("/signout")
async def signout(authorization: Optional[str] = Header(None)):
    if USE_SUPABASE and supabase:
        try:
            if authorization and authorization.startswith("Bearer "):
                supabase.auth.sign_out()
            return {"message": "Signed out successfully"}
        except Exception:
            raise HTTPException(status_code=400, detail="Signout failed")
    else:
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
            if token in FALLBACK_SESSIONS:
                del FALLBACK_SESSIONS[token]
        return {"message": "Signed out successfully"}


@router.get("/config")
async def get_supabase_config(user: Dict = Depends(get_current_user)):
    if not supabase_url or not supabase_key:
        raise HTTPException(status_code=404, detail="Supabase not configured")
    return {
        "supabaseUrl": supabase_url,
        "supabaseAnonKey": supabase_key
    }
