# ReconX AI — Deployment Guide (100% Free Stack)

ReconX AI supports both **local Docker Compose** execution (Decision `D9`) and **100% free cloud hosting** across PostgreSQL, FastAPI, and React/Vite.

---

## 1. Local Deployment (Docker Compose)

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Set a strong `JWT_SECRET` (at least 32 characters). Leave `LLM_PROVIDER=mock` for zero-cost offline execution (or supply a free Gemini/Groq key).

2. Start PostgreSQL, backend, and frontend:
   ```bash
   docker compose up --build -d
   ```

3. Run migrations and seed synthetic demo data inside the backend container:
   ```bash
   docker compose exec backend alembic upgrade head
   docker compose exec backend python scripts/seed.py --reset
   docker compose exec backend python scripts/make_sample_docs.py
   ```

4. Access:
   - Web UI: `http://localhost:5173`
   - FastAPI Swagger docs: `http://localhost:8000/api/v1/docs`
   - Health check: `GET http://localhost:8000/api/v1/health`

> **Environment Status Note (`OD-07`)**: During build verification on this Windows host, Docker Desktop daemon and native `psql` were unavailable locally, so migrations, triggers, and full API/E2E tests were verified via SQLite + FastAPI while preserving PostgreSQL DDL (`NUMERIC(18,4)`, `UUID`, triggers) in Alembic migrations. Run `docker compose up --build` in any Linux/Docker-enabled host to verify live PostgreSQL execution.

---

## 2. Free Cloud Hosting Options & Current Limits

> Always re-verify provider quotas before relying on free tiers in production. Snapshot verified below:

### A. Managed PostgreSQL (Free Tier)

| Provider | Storage Limit | Compute / Activity Rules | Trade-offs |
|---|---|---|---|
| **Neon Free** | **1 GB** per project | **100 CU-hours/month** per project; autoscales up to **2 CU**; scales to zero after **5 min** inactivity; 6-hour history window; 5 GB egress. | Cold start on first query after 5 min idle; hard cap stops project at 1 GB instead of auto-billing. |
| **Supabase Free** | **500 MB** DB + **1 GB** file storage per project | Up to **2 active projects** per org; shared CPU / 500 MB RAM; **5 GB** egress/mo; **pauses after 7 consecutive days** of inactivity. | No automated daily backups or PITR on free tier; manual unpause needed after 7 idle days. |

Set `DATABASE_URL` (SQLAlchemy psycopg3 URL, e.g., `postgresql+psycopg://USER:PASS@HOST/DB?sslmode=require`) on the backend service, then run `alembic upgrade head`.

### B. Backend FastAPI (Render Free Web Service)

- **Specs**: **512 MB RAM**, **0.1 CPU**.
- **Sleep / Cold Start**: Automatically **spins down after 15 minutes** of no inbound HTTP traffic; wakes in ~1 minute on the next request.
- **Monthly Quota**: **750 free instance hours/calendar month** per workspace (enough for 1 continuous service).
- **Important Ephemeral Storage Caveat**: Render Free Web Services use an **ephemeral local filesystem**. Uploaded files in `STORAGE_ROOT` and an unbacked in-memory SQLite file would wipe on spin-down. Always connect `DATABASE_URL` to **Neon** or **Supabase** PostgreSQL on Render, and treat uploaded documents as session/demo storage (or swap `StorageAdapter` for a free object store like Cloudflare R2 free tier later).
- **Build & Start commands on Render**:
  - Root Directory: `backend`
  - Build Command: `pip install -r requirements.txt` (or `pip install .`)
  - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### C. Frontend React SPA (Vercel Hobby or Netlify Free)

| Provider | Free Limits | Configuration | Caveats |
|---|---|---|---|
| **Vercel Hobby** | **100 GB** Fast Data Transfer/mo, 1M function invocations/mo, 4 CPU-hours/mo, 100 deploys/day, hard caps (no surprise billing). | Root Directory: `frontend`; Build: `npm run build`; Output: `dist`; Env: `VITE_API_BASE_URL=https://<your-render-backend>` (do not append `/api/v1`; `client.ts` adds it). | Strictly for non-commercial personal/hobby use. Add SPA rewrite `/* -> /index.html`. |
| **Netlify Free** | **300 credits/month** unified pool (approx. 20 credits/GB bandwidth, 15 credits/deploy, 10 credits/GB-hr compute); pauses when credits run out. | Base Dir: `frontend`; Build: `npm run build`; Publish: `frontend/dist`; Env: `VITE_API_BASE_URL`. | Frequent Git push builds consume credits (15 credits/deploy). |

### D. Free LLM Options (`LLM_PROVIDER`)
- `mock` (default): **\$0, offline, deterministic** — full 3-way match, regex/table/OCR extraction, risk rules, investigator, and copilot work with zero keys.
- `ollama`: **\$0, local** self-hosted models (`OLLAMA_BASE_URL`).
- `gemini` / `groq`: Optional free API keys with automatic timeout/retry fallback when absent or rate-limited.

---

## 3. Environment Variables Reference

Copy `.env.example` to `.env` before running locally or with Docker Compose (`docker-compose.yml` loads `.env` via `env_file: - .env`).

| Variable | Required in Prod | Default / Safe Dev Value | Notes |
|---|---|---|---|
| `APP_ENV` | Yes | `development` (`production` in cloud) | Enables strict production checks. |
| `JWT_SECRET` | Yes | `CHANGE_ME_LOCAL_DEV_SECRET_AT_LEAST_32_CHARS` | Minimum 32 chars in prod; generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. |
| `DATABASE_URL` | Yes | `postgresql+psycopg://reconx:reconx_local_dev@localhost:5432/reconx` | Use Neon/Supabase PostgreSQL URI (`postgresql+psycopg://...` or `postgres://...`) in prod, or `sqlite:///./reconx_demo.db` for local quickstart. |
| `LLM_PROVIDER` | No | `mock` | Supported values: `mock`, `gemini`, `groq`, `ollama`. |
| `GEMINI_API_KEY` | If `gemini` | empty | Google AI Studio free-tier key. |
| `GEMINI_MODEL` | No | `gemini-2.0-flash` | Gemini model ID. |
| `GROQ_API_KEY` | If `groq` | empty | Groq Cloud free-tier key. |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Groq model ID. |
| `OLLAMA_BASE_URL` | If `ollama` | `http://localhost:11434` | Local Ollama endpoint. |
| `OLLAMA_MODEL` | No | `llama3.2` | Local Ollama model tag. |
| `STORAGE_ROOT` | No | `./storage` | Local directory outside public web paths (`StorageAdapter`). |
| `MAX_UPLOAD_SIZE_MB` | No | `15` | Maximum upload file size in megabytes. |
| `CORS_ORIGINS` | Yes | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated exact frontend origin(s), e.g. `https://reconx-ai.vercel.app`. Never use `*` in production. |
| `FEATURE_EVIDENCE_GRAPH` | No | `true` | Toggle Financial Evidence Graph (`P2`). |
| `FEATURE_FINANCE_COPILOT` | No | `true` | Toggle read-only Finance Copilot (`P2`). |
| `FEATURE_ANOMALY_ML` | No | `true` | Toggle IsolationForest anomaly indicator (`P1`). |
| `FEATURE_CASH_VIEW` | No | `true` | Toggle Cash & Obligations Analytics (`P2`). |
| `FEATURE_REPORT_EXPORTS` | No | `true` | Toggle CSV/audit export endpoints (`P2`). |
| `VITE_API_BASE_URL` | Yes (Frontend) | `http://localhost:8000` | Backend origin **without** trailing `/api/v1` (`client.ts` appends `/api/v1`). |

---

## 4. Cold Starts & Keep-Warm Option (Free Tier)

1. **Why cold starts happen**:
   - **Render Free Web Service** spins down after **15 minutes** of inactivity (~30–50s first-request wakeup).
   - **Neon Free** scales compute to zero after **5 minutes** of inactivity (~0.5–2s DB wakeup).
   - **Supabase Free** pauses entire projects after **7 days** of zero activity (requires manual resume in dashboard).
2. **Simple Keep-Warm Option**:
   - Configure a free external HTTP monitor (e.g. UptimeRobot or a scheduled GitHub Actions workflow) to `GET https://<your-render-backend>/api/v1/health` every **10–14 minutes** during demo/business hours.
   - **Quota note**: Render Free caps workspace compute at **750 hours/month**, and Neon Free caps compute at **100 CU-hours/month**. Restricting keep-warm pings to active demo windows avoids exhausting monthly free quotas.

---

## 5. Switching `LLM_PROVIDER` (Offline Mock vs. Live Providers)

The demo ships with `LLM_PROVIDER=mock` so every flow runs deterministically offline with zero API keys. To switch providers:
- **Gemini (free API key)**: Set `LLM_PROVIDER=gemini` and `GEMINI_API_KEY=<key>` (optional `GEMINI_MODEL=gemini-2.5-flash`).
- **Groq (free API key)**: Set `LLM_PROVIDER=groq` and `GROQ_API_KEY=<key>` (optional `GROQ_MODEL=llama-3.3-70b-versatile`).
- **Ollama (local offline LLM)**: Run `ollama pull llama3.2`, then set `LLM_PROVIDER=ollama` and `OLLAMA_BASE_URL=http://localhost:11434`.

Deterministic financial math, matching rules, tolerances, and approvals stay identical across all providers.
