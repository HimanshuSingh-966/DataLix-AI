# 🎯 DataLix AI

<div align="center">

![DataLix AI Banner](https://img.shields.io/badge/DataLix-AI%20Powered%20Analytics-6366f1?style=for-the-badge)

**Transform Data into Insights Through Natural Conversation**

[![Version](https://img.shields.io/badge/version-4.1.0-blue.svg)](https://github.com/HimanshuSingh-966/DataLix-AI/releases)
[![Better Stack Badge](https://uptime.betterstack.com/status-badges/v1/monitor/2srpm.svg)](https://uptime.betterstack.com/?utm_source=status_badge)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Node](https://img.shields.io/badge/node-%3E%3D18.0.0-brightgreen.svg)](https://nodejs.org)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![Live Demo](https://img.shields.io/badge/demo-live-success.svg)](https://datalix-ai.vercel.app)

[🚀 Live Demo](https://datalix-ai.vercel.app) • [📝 Changelog](./CHANGELOG.md) • [🐛 Report Bug](https://github.com/HimanshuSingh-966/DataLix-AI/issues) • [✨ Request Feature](https://github.com/HimanshuSingh-966/DataLix-AI/issues)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Why DataLix AI?](#-why-datalix-ai)
- [Key Features](#-key-features)
- [Demo & Screenshots](#-demo--screenshots)
- [Quick Start](#-quick-start)
- [Usage Guide](#-usage-guide)
- [Architecture](#-architecture)
- [Deployment](#-deployment)
- [Contributing](#-contributing)
- [Support](#-support)

---

## 🎨 Overview

**DataLix AI** is a revolutionary conversational data analysis platform that democratizes data science. Simply upload your dataset and start asking questions in plain English—no SQL, Python, or Excel expertise required. Get instant insights, automated quality assessments, and beautiful visualizations through an intuitive chat interface powered by cutting-edge AI.

### 🎯 Perfect For

- 📊 **Business Analysts** - Quick insights without technical barriers
- 🎓 **Students & Researchers** - Explore data and learn patterns
- 💼 **Product Managers** - Make data-driven decisions faster
- 🚀 **Startups** - Analyze metrics without hiring data scientists
- 👨‍💻 **Developers** - Rapid prototyping and EDA

---

## 💡 Why DataLix AI?

<table>
<tr>
<td width="50%">

### 🚫 Traditional Approach
- ❌ Requires SQL/Python knowledge
- ❌ Steep learning curve
- ❌ Time-consuming setup
- ❌ Complex visualization libraries
- ❌ Manual data quality checks
- ❌ Lost analysis context

</td>
<td width="50%">

### ✅ DataLix AI Way
- ✅ Natural language queries
- ✅ Instant results
- ✅ Zero configuration
- ✅ Auto-generated charts
- ✅ AI-powered quality scoring
- ✅ Persistent sessions

</td>
</tr>
</table>

---

## 🌟 Key Features

### 💬 Conversational AI Analysis
```
You: "Show me the top 5 products by revenue"
DataLix: *generates bar chart* "Here are your top performers..."

You: "What about trends over time?"
DataLix: *creates line chart* "Revenue has increased 23% quarter-over-quarter..."
```

**Features:**
- 🧠 Context-aware conversations with memory
- 🔄 Multi-turn dialogue support
- 🤖 Dual AI provider support (Gemini & Groq) — both with **native tool calling**: the AI actually executes operations instead of describing them
- 📊 **Aggregation-aware charts** — "how many rows per category" plots counts (not raw IDs); "average/total X by Y" uses real grouping
- 🛡️ **Non-destructive by default** — "show me rows where…" previews matches without changing your data; mutations only when you explicitly ask
- ↩️ **Undo any change** — "reset the dataset" restores the original upload
- 🔢 **Top-N & sorting** — "top 5 by marks" / "who has the highest X" answered from the actual data
- 🧮 **Derived & renamed columns** — safe arithmetic formulas (`Price * Quantity`) and column renames
- 💡 Intelligent suggested next actions
- 🎯 Automatic query optimization

### 🤖 Multi-Agent Analysis Pipeline
One request — "analyze my data" — runs a full LangGraph pipeline of specialized subagents:

```
Ingestion → Diagnosis → Cleaning → Visualization → Insight
```

- 🔍 **Ingestion** profiles every column (types, cardinality, datetime detection)
- 🩺 **Diagnosis** produces a data quality report with issues and a 0–100 score
- 🧹 **Cleaning** fixes issues on a working copy with a full audit log
- 📊 **Visualization** auto-selects and generates the most relevant charts
- 💡 **Insight** writes an executive summary of findings

Available via chat ("run a full analysis") or directly through `POST /analyze`.

### 📊 Automated Data Quality Scoring

Get instant, comprehensive quality assessments:

| Category | What It Checks | Example Insights |
|----------|----------------|------------------|
| **Completeness** 📝 | Missing values, null patterns | "18% of email addresses are missing" |
| **Validity** ✅ | Data types, value ranges | "Price column has 3 negative values" |
| **Consistency** 🔄 | Duplicates, formatting | "42 duplicate customer IDs found" |
| **Accuracy** 🎯 | Outliers, anomalies | "5 outliers detected in age column" |

**Actionable Recommendations:**
- 🔧 Step-by-step improvement suggestions
- 📈 Priority-ranked issues
- 🎨 Visual quality dashboard
- 📊 Before/after comparison

### 📈 Rich Interactive Visualizations

**Chart Types:**
- 📊 **Bar Charts** - Compare categories
- 📈 **Line Charts** - Show trends over time
- 🎯 **Scatter Plots** - Explore relationships
- 🔥 **Heatmaps** - Visualize correlations
- 📦 **Box Plots** - Analyze distributions
- 🥧 **Pie Charts** - Show proportions

**Visualization Features:**
- 🎨 Fully interactive with Plotly.js
- 💾 Export as PNG/SVG/HTML
- 🔍 Zoom, pan, and hover details
- 📱 Responsive and mobile-friendly
- 🎯 Auto-selected chart types
- 🌈 Color-blind friendly palettes

### 💾 Advanced Session Management

Never lose your analysis progress:

- 💬 **Full Chat History** - All conversations preserved
- 📊 **Visualization Library** - Every chart saved
- 🔄 **Session Switching** - Work on multiple datasets
- ⏰ **Auto-save** - Changes saved in real-time
- 🗑️ **Session Cleanup** - Manage old analyses
- 📤 **Export Sessions** - Share insights with team

### 📁 Universal File Support

| Format | Extensions | Max Size |
|--------|-----------|----------|
| CSV | `.csv` | 100MB |
| Excel | `.xlsx`, `.xls` | 100MB |
| JSON | `.json` | 50MB |
| Parquet | `.parquet` | 100MB |

**Smart Upload Features:**
- 🚀 Drag & drop support
- 📊 Instant preview
- 🔍 Auto-detection of delimiters
- 📝 Encoding detection (UTF-8, Latin-1)
- ⚡ Streaming for large files

### 🎨 Modern User Experience

- 🌙 **Dark Mode Optimized** - Easy on the eyes
- ⌨️ **Keyboard Shortcuts** - Power user features
- 📱 **Fully Responsive** - Works on all devices
- ⚡ **Real-time Updates** - Instant feedback
- 🎯 **Intuitive Interface** - Minimal learning curve
- ♿ **Accessible** - WCAG 2.1 AA compliant

---

## 🎬 Demo

### 🔴 [Watch Live Demo](https://datalix-ai.vercel.app)


---

## 🚀 Quick Start

### Prerequisites Checklist

Before you begin, ensure you have:

- ✅ **Node.js 18+** ([Download](https://nodejs.org))
- ✅ **Python 3.11+** ([Download](https://python.org))
- ✅ **Git** ([Download](https://git-scm.com))
- ✅ **Supabase Account** ([Sign Up](https://supabase.com))
- ✅ **AI API Key** (at least one):
  - [Google Gemini API](https://makersuite.google.com/app/apikey), OR
  - [Groq API](https://console.groq.com)

### 📦 Installation

**Step 1: Clone & Navigate**
```bash
git clone https://github.com/HimanshuSingh-966/DataLix-AI.git
cd DataLix-AI
```

**Step 2: Install Dependencies**
```bash
# Install Node.js packages
npm install

# Install Python packages
pip install -r requirements.txt
```

**Step 3: Configure Environment**

Create `.env` file in root directory:

```env
# ========================================
# Supabase Configuration
# ========================================
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
DATABASE_URL=postgresql://postgres:[password]@db.your-project.supabase.co:5432/postgres

# ========================================
# AI Provider Keys (at least one required)
# ========================================
GEMINI_API_KEY=your-gemini-api-key
GROQ_API_KEY=your-groq-api-key

# ========================================
# Frontend Configuration
# ========================================
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key-here

# ========================================
# Server Configuration
# ========================================
NODE_ENV=development            # set to "production" in deployment (disables API docs + dev reload)
PORT=8001                       # FastAPI backend port (Render sets this automatically)
PYTHON_BACKEND_URL=http://localhost:8001   # used by the Vite dev proxy

# ========================================
# Security & Limits (optional — sensible defaults)
# ========================================
ALLOWED_ORIGINS=http://localhost:5000,http://localhost:3000
MAX_UPLOAD_MB=50
MAX_DATASET_ROWS=1000000
MAX_DATASET_COLUMNS=500
```

**Step 4: Initialize Database**

1. Open your [Supabase SQL Editor](https://app.supabase.com)
2. Run the script: `init_database_with_rls.sql` (repo root)
3. Verify tables are created

**Step 5: Launch Application**

```bash
# Terminal 1 — FastAPI backend (port 8001)
npm run dev:python

# Terminal 2 — React frontend with hot reload (port 5173)
npm run dev
```

The Vite dev server proxies `/api/*` to the backend automatically.

**Step 6: Access Application**

🎉 Open browser to: **http://localhost:5173**

### 🎯 First Steps

1. **Create Account** - Sign up with email/password
2. **Upload Dataset** - Try with sample CSV
3. **Review Quality** - Check automated assessment
4. **Ask Questions** - Start with: *"Show me a summary"*
5. **Explore** - Click suggested actions

---

## 📖 Usage Guide

### 🎓 Example Questions by Category

<details>
<summary><b>📊 Data Exploration</b></summary>

```
✨ Basic Overview
"What columns are in this dataset?"
"Show me the first 20 rows"
"How many rows and columns do I have?"
"What are the data types?"

📈 Statistical Summary
"Give me statistics for all numeric columns"
"What's the distribution of the age column?"
"Show me unique values in category"
"Calculate percentiles for price"

🔍 Data Inspection
"Find all missing values"
"Show me duplicate rows"
"What's the date range of this data?"
"List all unique product categories"
```

</details>

<details>
<summary><b>📈 Statistical Analysis</b></summary>

```
📊 Descriptive Statistics
"Calculate mean, median, mode for sales"
"Show standard deviation of prices"
"What's the variance in revenue?"
"Find the range of values"

🔗 Relationships
"Show correlation between price and sales"
"Create a correlation matrix"
"Find features correlated with target"
"Analyze relationship between X and Y"

🎯 Advanced Analysis
"Perform regression analysis"
"Calculate moving averages"
"Detect seasonal patterns"
"Find statistical significance"
```

</details>

<details>
<summary><b>📊 Visualization Requests</b></summary>

```
📊 Charts
"Create a bar chart of sales by region"
"Show line graph of revenue over time"
"Generate scatter plot of age vs income"
"Make a pie chart of market share"

🔥 Advanced Visualizations
"Show heatmap of correlations"
"Create box plot for price distribution"
"Generate histogram of ages"
"Make a stacked bar chart"

🎨 Customization
"Use different colors for the chart"
"Add trend line to scatter plot"
"Show top 10 values only"
"Group by month instead of day"
```

</details>

<details>
<summary><b>🧹 Data Cleaning</b></summary>

```
🔧 Handling Missing Data
"Remove rows with missing values"
"Fill missing prices with median"
"Drop columns with >50% missing data"
"Interpolate missing timestamps"

🎯 Data Transformation
"Remove duplicate entries"
"Standardize phone number format"
"Convert dates to standard format"
"Normalize numeric columns"

📊 Quality Improvement
"Identify and remove outliers"
"Fix inconsistent categories"
"Validate email addresses"
"Clean text columns"
```

</details>

### 💡 Pro Tips

| Tip | Description | Example |
|-----|-------------|---------|
| 🎯 **Be Specific** | Include column names | "Show sales in January" vs "Show data" |
| 🔄 **Follow Up** | Build on previous answers | "Now show it as a pie chart" |
| 📊 **Request Charts** | Explicitly ask for visualizations | "Create a bar chart of..." |
| 🎨 **Customize** | Specify preferences | "Top 10 only" or "group by month" |
| 💾 **Save Work** | Sessions auto-save | Come back anytime |

### ⌨️ Keyboard Shortcuts

- `Ctrl/Cmd + Enter` - Send message
- `Ctrl/Cmd + K` - Focus search
- `Esc` - Clear input
- `↑` - Previous message
- `↓` - Next message

---

## 🏗️ Architecture

### 🎯 System Design

```
┌─────────────────────────────────────────────────────────┐
│                     Client (React)                      │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐    │
│  │   Chat   │  │   Data   │  │  Visualization    │    │
│  │Interface │  │ Preview  │  │     Engine        │    │
│  └──────────┘  └──────────┘  └───────────────────┘    │
└────────────────────┬────────────────────────────────────┘
                     │
                     │  /api/* (Vercel rewrite / Vite proxy / nginx)
                     │
            ┌────────▼─────────┐
            │     FastAPI      │
            │    (Python)      │
            │                  │
            │  - Auth          │
            │  - Sessions      │
            │  - Data Analysis │
            │  - AI Chat       │
            │  - Agent Pipeline│
            │  - Visualizations│
            └────────┬─────────┘
                     │
┌────────────────────▼───┐
│   Supabase (Postgres)  │
│                        │
│  - Users               │
│  - Sessions            │
│  - Messages            │
│  - Datasets (metadata) │
└────────────────────────┘

    ┌─────────────────────────┐
    │     LangGraph Agents    │
    │                         │
    │  1. Ingestion Agent     │
    │  2. Diagnosis Agent     │
    │  3. Cleaning Agent      │
    │  4. Visualization Agent │
    │  5. Insight Agent       │
    └─────────────────────────┘

    ┌─────────────┐
    │  AI Providers│
    │             │
    │  - Gemini   │
    │  - Groq     │
    └─────────────┘
```

### 🛠️ Technology Stack

<table>
<tr>
<td width="50%">

#### **Frontend**
```typescript
React 18          // UI library
TypeScript        // Type safety
Wouter            // Routing
TanStack Query    // Data fetching
Shadcn UI         // Components
Tailwind CSS      // Styling
Plotly.js         // Charts
Zustand           // State management
```

</td>
<td width="50%">

#### **Backend**
```typescript
FastAPI           // Python API server
LangGraph         // Multi-agent pipeline
Supabase          // Database & Auth
PostgreSQL        // Data storage
```

</td>
</tr>
<tr>
<td width="50%">

#### **Data & AI**
```python
pandas            # Data manipulation
langgraph         # Multi-agent orchestration
langchain         # LLM pipelines
plotly            # Visualizations
google-generativeai # Gemini
groq              # Groq API
```

</td>
<td width="50%">

#### **DevOps**
```yaml
Docker            # Containerization
GitHub Actions    # CI/CD
Render            # Hosting
Supabase          # BaaS
Sentry (optional) # Error tracking
```

</td>
</tr>
</table>

### 📂 Project Structure

```
datalix-ai/
├── 📁 client/                    # React frontend
│   ├── 📁 src/
│   │   ├── 📁 components/        # Reusable UI components
│   │   │   ├── 📁 ui/            # Base components (shadcn)
│   │   │   ├── Chat.tsx          # Chat interface
│   │   │   ├── DataPreview.tsx   # Data table
│   │   │   └── Visualization.tsx # Chart renderer
│   │   ├── 📁 pages/             # Route pages
│   │   │   ├── Home.tsx          # Landing page
│   │   │   ├── Dashboard.tsx     # Main app
│   │   │   └── Auth.tsx          # Login/Signup
│   │   ├── 📁 lib/               # Utilities
│   │   │   ├── api.ts            # API client
│   │   │   ├── utils.ts          # Helpers
│   │   │   └── supabase.ts       # Supabase client
│   │   ├── 📁 hooks/             # Custom React hooks
│   │   │   ├── useChat.ts        # Chat logic
│   │   │   ├── useSession.ts     # Session management
│   │   │   └── useData.ts        # Data operations
│   │   └── main.tsx              # Entry point
│   ├── index.html
│   └── vite.config.ts
│
├── 📁 python_backend/            # FastAPI service
│   ├── main.py                   # FastAPI app
│   ├── data_processor.py         # Data analysis engine
│   ├── ai_chat.py                # AI integration
│   ├── quality_scorer.py         # Quality assessment
│   ├── visualization.py          # Chart generation
│   └── auth.py                   # Auth middleware
│
├── 📁 shared/                    # Shared TypeScript types
│   └── schema.ts                 # Data models
│
├── init_database_with_rls.sql    # Database schema + RLS policies
├── vercel.json                   # Vercel config (frontend + /api rewrite)
├── CHANGELOG.md                  # Version history
├── .env.example                  # Environment template
├── package.json                  # Node dependencies
├── requirements.txt              # Python dependencies
├── tsconfig.json                 # TypeScript config
├── vite.config.ts                # Vite config
└── README.md                     # This file
```

---

## 🚀 Deployment

### 🎯 Recommended: Backend on Render + Frontend on Vercel

The FastAPI backend runs as a Render Web Service; the React app is served as a static site from Vercel. The included `vercel.json` rewrites `/api/*` calls to the Render backend, so requests stay same-origin in the browser — no client code changes and no CORS friction.

**1. Deploy the Python backend to Render**

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"Web Service"** and connect your GitHub repository
3. Configure:
   - **Name:** `datalix-ai-backend`
   - **Root Directory:** `python_backend`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT --proxy-headers`
   - **Instance Type:** Free or Starter
4. Add environment variables (from `.env`):
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
   - `GEMINI_API_KEY`, `GROQ_API_KEY`
   - `NODE_ENV=production` (disables API docs + dev reload)
   - `ALLOWED_ORIGINS=https://your-app.vercel.app` (your Vercel domain — needed for any direct-to-backend calls)

**2. Deploy the frontend to Vercel**

1. Edit `vercel.json` — replace `YOUR-RENDER-BACKEND.onrender.com` with your actual Render service URL
2. Import the repository at [vercel.com/new](https://vercel.com/new)
3. Vercel picks up `vercel.json` automatically (`vite build` → `dist/public`)
4. Deploy — API calls to `/api/*` are transparently forwarded to Render

**3. Post-deploy checklist**

- ✅ Run `init_database_with_rls.sql` in the Supabase SQL editor (once)
- ✅ Confirm `https://<render-service>.onrender.com/health` returns healthy
- ✅ Sign up, upload a dataset, and send a chat message end-to-end
- ⚠️ Render free tier sleeps after inactivity — the first request after idle takes ~30–60s (the app shows a cold-start banner)

### 🐳 Docker Deployment

<details>
<summary>Click to expand Docker instructions</summary>

```bash
# Build images
docker-compose build

# Run services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

</details>

### ☁️ Other Platforms

| Platform | Best For | Guide |
|----------|----------|-------|
| **Vercel** | Frontend hosting | [Deploy Frontend →](https://vercel.com/docs) |
| **Railway** | Full-stack apps | [Deploy Railway →](https://railway.app/docs) |
| **Fly.io** | Global edge deployment | [Deploy Fly →](https://fly.io/docs) |
| **AWS** | Enterprise scale | [Deploy AWS →](https://aws.amazon.com/getting-started/) |

---

## 🔐 Security Features

- 🔒 **Row-Level Security (RLS)** — database-level access control on all tables
- 🔑 **Secure Authentication** — Supabase Auth with server-side JWT verification; fallback sessions expire after 24h
- 👤 **Session Ownership Enforcement** — every session-scoped endpoint verifies the authenticated user owns the session (responds 404 so IDs can't be probed)
- ⏱️ **Rate Limiting** — per-IP sliding window: auth 10/min, uploads 10/min, chat 30/min, pipeline 10/min, 120/min global
- 🌐 **CORS Allowlist** — origins restricted via `ALLOWED_ORIGINS`; no wildcard with credentials
- 📁 **Upload Validation** — extension allowlist (csv/xlsx/xls/json/parquet), 50 MB size cap, empty-file rejection, row/column caps against decompression bombs
- 🙊 **No Information Leakage** — internal errors are logged server-side and genericized; validation errors never echo submitted values (e.g. passwords); API docs disabled in production
- 🔐 **Password Policy** — minimum 8 characters; usernames restricted to safe characters
- 🛡️ **Security Headers** — `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` on every response
- 📝 **Audit Logging** — the cleaning pipeline records every automated action

---

## 🤝 Contributing

We love contributions! Here's how you can help:

### 🐛 Bug Reports

Found a bug? [Open an issue](https://github.com/HimanshuSingh-966/DataLix-AI/issues/new?template=bug_report.md) with:
- Clear description
- Steps to reproduce
- Expected vs actual behavior
- Screenshots if applicable

### ✨ Feature Requests

Have an idea? [Request a feature](https://github.com/HimanshuSingh-966/DataLix-AI/issues/new?template=feature_request.md) with:
- Use case description
- Expected behavior
- Alternative solutions considered

### 💻 Code Contributions

**Quick Start:**
```bash
# 1. Fork & clone
git clone https://github.com/HimanshuSingh-966/DataLix-AI.git

# 2. Create feature branch
git checkout -b feature/amazing-feature

# 3. Make changes & commit
git commit -m 'Add amazing feature'

# 4. Push & create PR
git push origin feature/amazing-feature
```

**Guidelines:**
- Follow existing code style
- Write clear commit messages
- Add tests for new features
- Update documentation
- Keep PRs focused and small

### 📋 Development Setup

```bash
# Install pre-commit hooks
npm run prepare

# Run tests
npm test

# Lint code
npm run lint

# Format code
npm run format
```

---

## 📊 Roadmap

### ✅ Version 4.0 (Released — July 2026)
- [x] 🤖 Native AI tool calling (Groq + Gemini) — chat executes operations
- [x] 🧠 Multi-agent LangGraph analysis pipeline (`/analyze`)
- [x] 💾 Dataset persistence & session restore across restarts
- [x] 🔐 Security hardening (ownership checks, rate limiting, upload validation)

### ✅ Version 4.1 (Released — July 2026)
- [x] 📊 Chart aggregation (count/sum/mean/median/min/max) — fixes "number of rows per category" charts
- [x] 🛡️ Non-destructive filters — "show me..." views data without mutating; `reset_dataset` undoes any change
- [x] 🔢 Top-N & sorting — "top 5 by marks" / "who has the highest X" answered from real data
- [x] 🧮 Derived & renamed columns — safe arithmetic formulas, column rename
- [x] 🔍 Inspect-only duplicates view, datetime-aware filtering
- [x] 🤝 Unified tool schemas across providers (Groq now has correlation + ML)
- [x] 🗂️ Working session sidebar (select/rename/delete) — fixed field-mismatch crash

### 🚀 Version 4.2 (Planned)
- [ ] 💬 Persist chat history to database (the `messages` endpoint currently returns empty)
- [ ] 🔄 Real-time collaboration
- [ ] 📊 Advanced statistical tests
- [ ] 🎨 Custom chart themes
- [ ] 📤 Export to PowerPoint
- [ ] 🤖 AutoML integration
- [ ] 📈 Predictive analytics
- [ ] 🔄 Data pipeline builder
- [ ] 👥 Team workspaces
- [ ] 📱 Mobile app

### 🌟 Future Ideas
- [ ] 🔗 Database connectors
- [ ] 🎯 Scheduled reports
- [ ] 🌍 Multi-language support
- [ ] 🎨 White-labeling
- [ ] 🔐 SSO integration


---

## 📞 Support

### 💬 Get Help

- 📝 [Changelog](./CHANGELOG.md)
- 🐛 [GitHub Issues](https://github.com/HimanshuSingh-966/DataLix-AI/issues)
- 📧 Email: choudharyhimanshusingh966@gmail.com

### 🌟 Show Your Support

If DataLix AI helped you, please:
- ⭐ Star this repository
- 🐦 Share on Twitter
- 📝 Write a blog post
- 💬 Tell your colleagues

### 📊 Analytics

<div align="center">

![GitHub stars](https://img.shields.io/github/stars/HimanshuSingh-966/DataLix-AI?style=social)
![GitHub forks](https://img.shields.io/github/forks/HimanshuSingh-966/DataLix-AI?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/HimanshuSingh-966/DataLix-AI?style=social)

</div>

---

## 📝 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

**TL;DR:** You can use, modify, and distribute this software freely, even for commercial purposes.

---

## 🙏 Acknowledgments

Built with ❤️ using these amazing tools:

- **[Replit](https://replit.com)** - Development environment
- **[Shadcn UI](https://ui.shadcn.com)** - Beautiful components
- **[Plotly](https://plotly.com)** - Interactive charts
- **[Supabase](https://supabase.com)** - Backend infrastructure
- **[Google Gemini](https://deepmind.google/technologies/gemini/)** - AI intelligence
- **[Groq](https://groq.com)** - Fast inference
- **[Tailwind CSS](https://tailwindcss.com)** - Styling framework
- **[React](https://react.dev)** - UI library


---

## 📈 Stats

<div align="center">

![Repo Size](https://img.shields.io/github/repo-size/HimanshuSingh-966/DataLix-AI)
![Code Size](https://img.shields.io/github/languages/code-size/HimanshuSingh-966/DataLix-AI)
![Last Commit](https://img.shields.io/github/last-commit/HimanshuSingh-966/DataLix-AI)
![Issues](https://img.shields.io/github/issues/HimanshuSingh-966/DataLix-AI)
![Pull Requests](https://img.shields.io/github/issues-pr/HimanshuSingh-966/DataLix-AI)

</div>

---

<div align="center">

**[⬆ Back to Top](#-datalix-ai)**

Made with ❤️ for data enthusiasts everywhere

**[Website](https://datalix-ai.vercel.app)** • **[GitHub](https://github.com/HimanshuSingh-966/DataLix-AI)** • **[Changelog](./CHANGELOG.md)**

</div>
