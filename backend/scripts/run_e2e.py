"""Start backend + frontend temporarily, run Playwright E2E smoke test, then clean up."""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


def wait_for_url(url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=2.0)
            if r.status_code < 500:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for {url}")


def _kill_proc(proc: subprocess.Popen) -> None:
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        proc.terminate()
        proc.wait(timeout=5)


def main() -> int:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = Path(tmp) / "e2e_demo.db"
        storage_dir = Path(tmp) / "storage"
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
        env["STORAGE_ROOT"] = str(storage_dir)
        env["JWT_SECRET"] = "e2e-test-secret-at-least-32-chars-long"
        env["LLM_PROVIDER"] = "mock"
        env["WORKER_ENABLED"] = "true"
        env["SEED_DEFAULT_PASSWORD"] = "ReconXDemo#2026!"

        py = str(BACKEND / ".venv" / "Scripts" / "python.exe")
        print("1. Seeding fresh E2E database...")
        subprocess.run([py, "scripts/seed.py", "--reset"], cwd=BACKEND, env=env, check=True)

        print("2. Starting FastAPI backend on :8000...")
        be = subprocess.Popen(
            [py, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=BACKEND,
            env=env,
        )
        print("3. Starting Vite frontend on :5173...")
        fe_env = env.copy()
        fe_env["VITE_API_BASE_URL"] = "http://127.0.0.1:8000"
        fe = subprocess.Popen(
            ["cmd", "/c", "npm", "run", "dev", "--", "--port", "5173"],
            cwd=FRONTEND,
            env=fe_env,
        )

        try:
            wait_for_url("http://127.0.0.1:8000/api/v1/health", timeout=30.0)
            wait_for_url("http://127.0.0.1:5173", timeout=30.0)
            print("4. Running Playwright smoke test...")
            res = subprocess.run(
                ["cmd", "/c", "npx", "playwright", "test"],
                cwd=FRONTEND,
                env=fe_env,
            )
            return res.returncode
        finally:
            _kill_proc(fe)
            _kill_proc(be)


if __name__ == "__main__":
    sys.exit(main())
