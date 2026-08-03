# Deployment Guide — Apex Strategy v4

This document covers how to deploy the F1 Monte Carlo Race Strategy Simulator
using **Render** (backend) and **Vercel** (frontend) on their free tiers.

---

## Architecture

```
┌─────────────────┐        HTTPS        ┌─────────────────┐
│   Vercel (CDN)  │  ───────────────▶   │  Render (API)   │
│  React/Vite SPA │  VITE_API_BASE_URL  │  FastAPI/Uvicorn │
│  frontend/dist/ │                     │  backend/        │
└─────────────────┘                     └─────────────────┘
```

---

## Environment Variables

### Render (Backend)

| Variable | Required | Example Value | Notes |
|----------|----------|---------------|-------|
| `PORT` | Auto-set by Render | `10000` | **Do not set manually.** Render injects this automatically. |
| `ALLOWED_ORIGINS` | Yes | `https://your-app.vercel.app` | Comma-separated list of allowed CORS origins. Set to your Vercel frontend URL. |
| `FASTF1_CACHE_DIR` | Optional | `/tmp/fastf1_cache` | Where FastF1 caches telemetry data. Defaults to `backend/cache/` locally. Use `/tmp/fastf1_cache` on Render (ephemeral filesystem). |

### Vercel (Frontend)

| Variable | Required | Example Value | Notes |
|----------|----------|---------------|-------|
| `VITE_API_BASE_URL` | Yes | `https://your-api.onrender.com` | Full URL to your deployed Render backend. **No trailing slash.** |

---

## Step-by-Step Deployment

### 1. Deploy Backend to Render

1. Go to [render.com](https://render.com) and create a new **Web Service**
2. Connect your GitHub repo
3. Configure:
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free
4. Add environment variables:
   - `ALLOWED_ORIGINS` = `https://your-app.vercel.app` (update after you know the Vercel URL)
   - `FASTF1_CACHE_DIR` = `/tmp/fastf1_cache`
5. Deploy. Note your Render URL (e.g. `https://f1-simulator-api.onrender.com`)

> **Note**: The free tier spins down after 15 minutes of inactivity.
> First request after idle will take ~30 seconds (cold start).
> The frontend has a "Waking up..." overlay to handle this gracefully.

### 2. Deploy Frontend to Vercel

1. Go to [vercel.com](https://vercel.com) and import your GitHub repo
2. Configure:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
3. Add environment variable:
   - `VITE_API_BASE_URL` = `https://f1-simulator-api.onrender.com` (your Render URL from step 1)
4. Deploy. Note your Vercel URL.
5. **Go back to Render** and update `ALLOWED_ORIGINS` to your Vercel URL.

### 3. Verify

1. Visit your Vercel URL
2. You should see the "Waking up..." overlay on first visit (cold start)
3. After ~30s, the app should load with pre-populated defaults
4. Click "▶ Run Demo Scenario" to test the headline feature
5. Test all tabs: Monte Carlo, Undercut, Optimizer, Race Sim

---

## Local Development

```bash
# Backend
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8005

# Frontend (in a separate terminal)
cd frontend
npm run dev
```

The Vite dev server proxies API calls to `localhost:8005` automatically.
No environment variables needed for local development.

---

## FastF1 Calibration

The `/fastf1/calibrate` endpoint attempts to fetch live telemetry data from the
F1 API via the FastF1 library. This can be slow (5-15 seconds) on first call.

**Production behavior**: If FastF1 network access fails (common on free tiers),
the endpoint falls back to pre-computed static calibration data
(`CALIBRATED_BAHRAIN_2023`) that is hardcoded in `fastf1_calibrator.py`.
The app will not crash on a fresh deploy with an empty cache.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Waking up..." hangs forever | Backend crashed or failed to deploy | Check Render logs |
| CORS errors in browser console | `ALLOWED_ORIGINS` not set correctly | Update to match your exact Vercel URL |
| "Failed to fetch" errors | `VITE_API_BASE_URL` not set on Vercel | Add the env var and redeploy |
| FastF1 calibration returns "Offline Cache" | Network access blocked on free tier | Expected behavior — uses static fallback |
| Blank page on Vercel | Build failed | Check Vercel build logs, run `npm run build` locally |
