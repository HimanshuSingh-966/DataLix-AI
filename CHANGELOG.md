# Changelog

All notable changes to DataLix AI are documented in this file.

---

# DataLix AI v4.0.0 — "Actions, Not Answers"

**Release Date:** July 20, 2026
**Status:** Production Ready

The theme of this release: **the AI now does things instead of describing them.** Chat requests execute real operations through native tool calling, a full multi-agent analysis pipeline is live, datasets survive restarts, and the platform received a comprehensive security hardening pass.

---

## 🚀 Major Features

### 1. 🤖 Native AI Tool Calling (Groq) — REWRITTEN

The Groq provider previously relied on a fragile keyword protocol: the model was asked to embed magic strings (`REMOVE_COLUMNS:`, `CREATE_CHART:`, …) in its prose, which were then regex-parsed. When the model phrased things differently, nothing executed — users got "here are the steps you could take" instead of results.

**Now:**
- Groq uses **native OpenAI-style function calling** (`llama-3.3-70b-versatile`, `tool_choice="auto"`) with 8 typed tool schemas
- Tool calls are executed server-side, then a follow-up completion produces a natural-language summary of what was actually done
- A shared `_execute_tool()` executor serves both the Gemini and Groq paths — one implementation, consistent behavior
- **Removed:** all keyword regex parsing, and a dangerous "keyword sniffer" that silently ran mean-imputation on the dataset whenever the AI's reply merely mentioned "missing"/"impute"/"fill"

**Result:** "remove the region column" removes the column. "Show me a bar chart" returns a chart. Pure questions trigger no tools and never mutate data.

### 2. 🧠 Multi-Agent Analysis Pipeline — WIRED IN

The LangGraph subagent pipeline (ingestion → diagnosis → cleaning → visualization → insight) existed in the codebase but was never reachable from any endpoint.

**Now:**
- New **`POST /analyze`** endpoint runs the full pipeline: returns a quality report, cleaning audit log, auto-generated charts, and an AI-written executive summary
- New **`run_full_analysis`** tool on both AI providers — chat requests like "analyze my data" trigger the pipeline conversationally
- "Run Full Analysis" added to suggested actions after upload
- Pipeline bug fixes: decommissioned Groq model (`llama3-8b-8192` → `llama-3.3-70b-versatile`), crash guard on the no-LLM fallback summary, removed a pandas-2.x-incompatible argument

### 3. 💾 Dataset Persistence & Session Restore — FIXED

Dataset persistence to Supabase was **silently failing on every single upload**: the `datasets` table has a foreign key to `sessions`, but no code ever created the parent `sessions` row. The error was caught and swallowed, so sessions only lived in server memory and vanished on restart.

**Now:**
- The `sessions` row is upserted before the `datasets` row — persistence actually works
- `GET /sessions` merges in-memory sessions with persisted ones, so **sessions are listed and usable after a backend restart** (lazy restore pulls the dataset back from Supabase on first use)
- Data mutations (column removal, filtering, cleaning) are re-persisted, so changes survive restarts too
- Deleting a session now also deletes its persisted rows (with FK cascade)

---

## 🔐 Security Hardening

- **Session ownership enforcement** — all 9 session-scoped endpoints (`/chat`, `/analyze`, `/statistics`, `/correlation`, `/visualize`, `/clean`, `/ml-analysis`, `/export`, `DELETE /sessions/{id}`) verify the authenticated user owns the session. Unauthorized access returns **404** so session IDs can't be probed. Previously, any signed-in user could read, modify, or delete any other user's data by guessing a session ID.
- **Rate limiting** — per-IP sliding window: `/auth/*` 10/min (brute-force protection), `/upload` 10/min, `/analyze` 10/min, `/chat` 30/min, 120/min global. CORS preflights exempt; `Retry-After` header on 429s.
- **CORS fixed** — `allow_origins=["*"]` combined with credentials replaced by an explicit allowlist from `ALLOWED_ORIGINS`.
- **Upload validation** — extension allowlist enforced at the endpoint (csv/xlsx/xls/json/parquet), empty files rejected, 50 MB size cap (HTTP 413), and row/column caps (1M rows / 500 columns, configurable) against compressed files that expand enormously in memory.
- **No information leakage** — internal errors are logged server-side and replaced with generic messages (user-actionable `ValueError`s pass through); signup no longer echoes raw Supabase errors; **422 validation responses no longer echo submitted values (including passwords)**; API docs (`/docs`, `/openapi.json`) disabled in production.
- **Password & username policy** — minimum 8-character passwords; usernames restricted to `[a-zA-Z0-9_.-]`, 2–32 chars.
- **Security headers** — `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer` on all responses.

---

## 🐛 Bug Fixes

- ✅ Chart serialization crash: Plotly figures contained numpy arrays that FastAPI/pydantic couldn't serialize — charts now round-trip through Plotly's JSON encoder (fixed in both `visualizations.py` and the pipeline's visualization agent)
- ✅ Silent auto-imputation removed: the AI can no longer mutate data unless a tool is explicitly invoked
- ✅ `bcrypt` pinned to 4.0.1 (`passlib` 1.7.4 is incompatible with bcrypt ≥ 4.1 — fresh installs crashed on signup)
- ✅ Dev auto-reload disabled in production; proxy headers enabled so rate limiting sees real client IPs behind Render/nginx
- ✅ Test suite fixed: broken import in `test_fixes.py`, non-unique usernames in `test_all.py` colliding with the `profiles` unique constraint — **11/11 tests pass**
- ✅ HTTP status correctness: 413 for oversized uploads, 404s no longer masked as 400s

---

## 🗑️ Removed

- **The entire Node.js/Express layer** (`server/`, ~870 lines). Its proxy role is now handled by Vercel rewrites (cloud), nginx (Docker), or the Vite dev proxy (local). It also contained ~700 lines of unreachable route/storage code — registered after the catch-all proxy, so it never executed — including an unsecured parallel implementation of session endpoints. Nine npm dependencies dropped with it (express, http-proxy-middleware, postgres, tsx, esbuild, cross-env, groq-sdk, @google/generative-ai, @neondatabase/serverless).
- Keyword-protocol parsing and auto-imputation sniffer in the Groq path (~150 lines of regex)
- Dead files: `fix.py` (one-off script), `StatisticsCards.tsx`, `AuditLog.tsx`, `ui/alert.tsx` (unreferenced components)
- Verified via import-graph reachability analysis: every remaining frontend file is reachable from the app entry point

---

## 🚀 Deployment

- New **`vercel.json`** — frontend deploys to Vercel as a static site; `/api/*` is rewritten to the Render backend (same-origin from the browser, no client changes, no CORS friction)
- Recommended topology: **backend on Render** (`python_backend/`, uvicorn with `--proxy-headers`) + **frontend on Vercel**
- New environment variables (all optional, sensible defaults): `ALLOWED_ORIGINS`, `MAX_UPLOAD_MB`, `MAX_DATASET_ROWS`, `MAX_DATASET_COLUMNS`

---

## ⚠️ Notes

- Chat history is still memory-only (the `messages` table exists but is unused) — planned for v4.1
- The in-memory rate limiter is per-process; if you scale to multiple replicas, move limits to Redis or the reverse proxy

---
---

# Changelog - DataLix AI v3.0.0

## What's New - Chat-First Data Analysis Platform

This document outlines the complete transformation from Streamlit-based data cleaning tool to a modern, chat-first conversational data analysis platform.

**Release Date:** November 15, 2025
**Version:** 3.0.0
**Status:** Production Ready

---

## 🎯 Platform Transformation

### From: Streamlit Data Cleaning Tool
### To: Conversational AI Data Analysis Platform

**Core Philosophy Change:**
- v2.0: Manual, UI-driven data cleaning workflows
- v3.0: Natural language, AI-powered data conversation

---

## 🚀 Major New Features

### 1. 💬 AI-Powered Conversational Interface (NEW)
- Natural language queries for data analysis with context-aware conversations
- Google Gemini + Groq provider support with fallback
- Automatic function calling for data operations, suggested next actions
- Modern chat UI: markdown rendering, timestamps, auto-scroll, typing indicators

### 2. 📊 Automated Data Quality Scoring (NEW)
- Completeness, validity, consistency, and accuracy scores → weighted 0–100 composite
- Automatic assessment on upload with issue identification and recommendations
- Missing value patterns, duplicates, outliers (IQR), high-cardinality warnings

### 3. 🎨 Rich Interactive Visualizations (NEW)
- Bar, line, scatter, box, heatmap and custom Plotly charts embedded in chat
- Zoom/pan/hover, PNG export, dark-mode optimized, natural-language chart generation

### 4. 💾 Session Persistence & Management (NEW)
- Multiple analysis sessions with Supabase PostgreSQL storage and RLS isolation
- Sidebar session browser with switching and deletion

### 5. 🔐 Authentication & User Management (NEW)
- Email/password auth via Supabase Auth, JWT-based API authentication
- Row-level security for per-user data isolation

### 6. 📁 Advanced File Upload System (NEW)
- CSV, Excel (.xlsx/.xls), JSON, Parquet with drag-and-drop
- FastAPI + pandas processing with automatic quality assessment

### 7. 🎯 Suggested Actions System (NEW)
- Context-aware one-click recommendations based on dataset state

### 8. 🎨 Modern UI/UX Redesign (COMPLETE OVERHAUL)
- React 18 + TypeScript, Wouter, TanStack Query, Shadcn UI, Tailwind CSS

### 9. 🔧 Backend Architecture (NEW)
- Hybrid Node.js (Express gateway/proxy) + Python (FastAPI processing) backend

### 10. 📊 Data Processing Pipeline (ENHANCED)
- Quality scoring engine, correlation/distribution analysis, outlier detection (IQR, Z-score, Isolation Forest)

---

## 🗑️ Features Removed (From v2.0)

Streamlit-based manual workflows replaced with AI-chat equivalents: database connector UI, ML cleaning page, batch processing UI, workflow pipeline builder, dashboard builder — all now achievable through natural language conversation.

---

## 🔄 Architecture Changes

- **Database:** Supabase PostgreSQL with RLS policies, UUID keys, JSONB storage
- **Frontend:** React + TypeScript with Vite, TanStack Query, Zustand
- **Backend:** Node.js (port 5000, gateway) + Python FastAPI (port 8001, processing)

---

## 🐛 Bug Fixes

- ✅ Fixed UUID/varchar schema mismatch in session creation
- ✅ Resolved TypeScript array conversion errors in Supabase storage
- ✅ Fixed JSONB serialization for complex message data
- ✅ Corrected PostgreSQL RowList iteration

---

## 📝 Breaking Changes

**Complete Platform Rewrite:** all v2.0 code replaced, new database schema, new API structure, new authentication system. No backward compatibility — v2.0 data requires manual migration.

---

**Version**: 3.0.0
**Release Date**: November 15, 2025
**Status**: Production Ready - Complete Platform Transformation
