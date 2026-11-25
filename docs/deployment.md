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
| **Vercel Hobby** | **100 GB** Fast Data Transfer/mo, 1M function invocations/mo, 4 CPU-hours/mo, 100 deploys/day, hard caps (no surprise billing). | Root Directory: `frontend`; Build: `npm run build`; Output: `dist`; Env: `VITE_API_BASE_URL=https://<your-render-backend>/api/v1`. | Strictly for non-commercial personal/hobby use. Add SPA rewrite `/* -> /index.html`. |
| **Netlify Free** | **300 credits/month** unified pool (approx. 20 credits/GB bandwidth, 15 credits/deploy, 10 credits/GB-hr compute); pauses when credits run out. | Base Dir: `frontend`; Build: `npm run build`; Publish: `frontend/dist`; Env: `VITE_API_BASE_URL`. | Frequent Git push builds consume credits (15 credits/deploy). |

### D. Free LLM Options (`LLM_PROVIDER`)
- `mock` (default): **\$0, offline, deterministic** — full 3-way match, regex/table/OCR extraction, risk rules, investigator, and copilot work with zero keys.
- `ollama`: **\$0, local** self-hosted models (`OLLAMA_BASE_URL`).
- `gemini` / `groq`: Optional free API keys with automatic timeout/retry fallback when absent or rate-limited.
