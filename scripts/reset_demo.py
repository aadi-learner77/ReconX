"""Cross-platform deterministic demo reset script for ReconX AI.

Resets database tables, seeds deterministic synthetic organizations/users/vendors/POs/GRNs/invoices,
and regenerates local sample documents in `sample_data/`.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"


def main() -> int:
    env = os.environ.copy()
    env.setdefault("DATABASE_URL", "sqlite:///./reconx_demo.db")

    venv_py = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
    if not venv_py.exists():
        venv_py = BACKEND_DIR / ".venv" / "bin" / "python"
    python_exe = str(venv_py) if venv_py.exists() else sys.executable

    seed_cmd = [python_exe, str(BACKEND_DIR / "scripts" / "seed.py"), "--reset"]
    docs_cmd = [python_exe, str(BACKEND_DIR / "scripts" / "make_sample_docs.py")]

    print(f"1/2 Resetting and seeding synthetic dataset ({env['DATABASE_URL']})...")
    res1 = subprocess.run(seed_cmd, cwd=str(BACKEND_DIR), env=env, check=False)
    if res1.returncode != 0:
        return res1.returncode

    print("2/2 Regenerating sample documents in sample_data/...")
    res2 = subprocess.run(docs_cmd, cwd=str(BACKEND_DIR), env=env, check=False)
    return res2.returncode


if __name__ == "__main__":
    raise SystemExit(main())
