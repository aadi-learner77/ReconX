# ReconX AI — Neo4j Setup & Operations Guide

## 1. Docker Compose Startup
```powershell
docker compose up -d --build
docker compose exec -T backend python scripts/seed.py --reset
```
- **Neo4j Browser:** `http://localhost:7474` (Bolt: `bolt://localhost:7687`)
- **ReconX Frontend:** `http://localhost:5173`
- **ReconX API:** `http://localhost:8000`

## 2. Backfill & Health Commands
- Check sync health: `GET /api/v1/graph/health`
- Trigger full org backfill (Admin): `POST /api/v1/graph/sync/backfill`
- Retry failed outbox events (Admin): `POST /api/v1/graph/sync/retry-failed`
