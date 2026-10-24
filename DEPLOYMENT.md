# Deployment Guide — Apex Strategy v5

This document covers how to deploy the F1 Monte Carlo Race Strategy Simulator
using **Render** (backend) and **Vercel** (frontend) on their free tiers, along with
security advisory compliance for Node.js and CA certificates.

---

## Architecture

```
┌─────────────────┐        HTTPS        ┌─────────────────────────┐
│   Vercel (CDN)  │  ───────────────▶   │      Render (API)       │
│  React/Vite SPA │  VITE_API_BASE_URL  │ FastAPI / Uvicorn (app) │
│  frontend/dist/ │                     │ backend/app/            │
└─────────────────┘                     └─────────────────────────┘
```

---

## 🔒 Security Advisory Compliance (Render & Vercel)

### 1. eMudhra Intermediate Certificate Compromise
* **Risk**: Compromised private keys for eight intermediate certificates issued by eMudhra can allow attackers to intercept or impersonate HTTPS endpoints.
* **Backend Mitigation**: Python's `requests` and `httpx` HTTP clients depend on `certifi` for trusted Mozilla CA roots. The backend pins `certifi>=2024.7.4` in `requirements.txt`.
* **Action Required**: When deploying or rebuilding on Render, Render's native runtime automatically updates the system certificate store, and pip installs the patched `certifi` package.

### 2. Node.js Security Release (Brotli RCE & TLS Bypass)
* **Risk**: Vulnerabilities in older Node.js runtimes allowed TLS certificate hostname bypasses and Brotli remote code execution.
* **Mitigation**: Node.js has been pinned to `>=22.23.4` via:
  - `frontend/package.json` (`"engines": { "node": ">=22.23.4" }`)
  - `frontend/.node-version` (`22.23.4`)
  - Project root `.node-version` (`22.23.4`)
* **Action Required**: Vercel and Render automatically detect `.node-version` and build the frontend using the patched Node.js 22 release.

---

## Environment Variables

### Render (Backend)

| Variable | Required | Example Value | Notes |
|----------|----------|---------------|-------|
| `PORT` | Auto-set by Render | `10000` | **Do not set manually.** Render injects this automatically. |
| `ALLOWED_ORIGINS` | Yes | `https://your-app.vercel.app` | Comma-separated list of allowed CORS origins. Set to your Vercel frontend URL (or `*` during initial testing). |
| `FASTF1_CACHE_DIR` | Optional | `/tmp/fastf1_cache` | Where FastF1 caches telemetry data. Defaults to `/tmp/fastf1_cache` on ephemeral cloud hosts. |

### Vercel (Frontend)

| Variable | Required | Example Value | Notes |
|----------|----------|---------------|-------|
| `VITE_API_BASE_URL` | Yes | `https://f1-monte-carlo-race-strategy-simulator.onrender.com` | Full URL to your deployed Render backend. **No trailing slash.** |

---

## Step-by-Step Deployment

### 1. Deploy Backend to Render

1. Go to [render.com](https://render.com) and create a new **Web Service**.
2. Connect your GitHub repository: `jvstin47/f1-monte-carlo-race-strategy-simulator`.
3. Configure settings:
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Instance Type**: Free
4. Add environment variables:
   - `ALLOWED_ORIGINS` = `*` (or your Vercel URL once known)
   - `FASTF1_CACHE_DIR` = `/tmp/fastf1_cache`
5. Click **Create Web Service**. Note your Render URL (e.g. `https://f1-monte-carlo-race-strategy-simulator.onrender.com`).

> **Cold Start Note**: The free tier spins down after 15 minutes of inactivity.
> The first request after idle takes ~30 seconds. The frontend includes a dedicated
> cold-start overlay that monitors the `/health` endpoint to inform visitors.

### 2. Deploy Frontend to Vercel

1. Go to [vercel.com](https://vercel.com) and import your GitHub repository.
2. Configure settings:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Vite
   - **Node.js Version**: 22.x (automatically inferred from `.node-version`)
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
3. Add environment variable:
   - `VITE_API_BASE_URL` = `https://f1-monte-carlo-race-strategy-simulator.onrender.com` (your Render backend URL)
4. Click **Deploy**. Note your Vercel URL (e.g. `https://f1-monte-carlo.vercel.app`).
5. **Update Render CORS**: Return to Render Dashboard → Environment Variables, and set `ALLOWED_ORIGINS` to your exact Vercel URL.

### 3. Verification Checklist

1. Visit `https://your-api.onrender.com/health` → verify response `{"status":"ok"}`.
2. Visit `https://your-api.onrender.com/docs` → verify interactive Swagger UI loads with both root and `/api/v1` routes.
3. Visit your Vercel URL → verify the dashboard loads with pre-populated track and driver data.
4. Click **"▶ Run Demo Scenario"** to confirm end-to-end Monte Carlo simulation execution.

---

## Local Development

```bash
# 1. Start Backend API
cd backend
source venv/bin/activate
python main.py

# 2. Start Frontend Dev Server (in a separate terminal)
cd frontend
npm run dev
```

* Frontend: `http://localhost:3000`
* Backend API: `http://localhost:8005`
* Swagger UI: `http://localhost:8005/docs`

The Vite dev server proxies API calls to `http://127.0.0.1:8005` automatically.
