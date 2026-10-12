"""Hermetic runtime world manager for ProofQA targets."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx

from proofqa.contracts import WorldSpec

REPO_ROOT = Path(__file__).resolve().parents[2]


def find_free_port() -> int:
    """Find and return an unused TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class World:
    """Context manager for an isolated, reproducible test environment instance."""

    def __init__(self, spec: WorldSpec) -> None:
        self.spec = spec
        self.port: int = 0
        self.url: str = ""
        self.temp_dir: Path | None = None
        self.runtime_db: Path | None = None
        self.seed_db: Path = REPO_ROOT / spec.seed_db
        self.process: subprocess.Popen | None = None
        self.startup_time_ms: float = 0.0

    def start(self, timeout_sec: float = 12.0) -> World:
        """Initialize temp directory, copy seed database, launch target on free port, and wait for healthcheck."""
        start_t = time.perf_counter()

        if not self.seed_db.exists():
            from apps.shop_twin.backend.seed import seed_database
            seed_database(self.seed_db)

        # 1. Create hermetic temp dir
        self.temp_dir = Path(tempfile.mkdtemp(prefix="proofqa_world_"))
        self.runtime_db = self.temp_dir / "runtime.db"
        shutil.copyfile(self.seed_db, self.runtime_db)

        # 2. Pick free port
        self.port = find_free_port()
        self.url = f"http://127.0.0.1:{self.port}"

        # 3. Build isolated environment
        env = os.environ.copy()
        env["BUGS"] = ",".join(self.spec.bugs)
        env["SEED"] = str(self.spec.seed)
        env["CLOCK_ISO"] = self.spec.clock_iso
        env["SHOP_DB_PATH"] = str(self.runtime_db)
        env["PORT"] = str(self.port)
        env["PYTHONPATH"] = str(REPO_ROOT)

        # 4. Launch backend process
        python_exe = sys.executable
        app_script = REPO_ROOT / "apps" / "shop_twin" / "backend" / "main.py"
        self.process = subprocess.Popen(
            [python_exe, str(app_script), str(self.port)],
            env=env,
            cwd=str(REPO_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # 5. Wait for /api/health
        health_url = f"{self.url}/api/health"
        deadline = time.time() + timeout_sec
        healthy = False
        while time.time() < deadline:
            try:
                res = httpx.get(health_url, timeout=0.5)
                if res.status_code == 200 and res.json().get("status") == "ok":
                    healthy = True
                    break
            except Exception:
                pass
            time.sleep(0.1)

        if not healthy:
            self.stop()
            raise RuntimeError(f"World failed to become healthy at {health_url} within {timeout_sec}s")

        self.startup_time_ms = (time.perf_counter() - start_t) * 1000.0
        return self

    def reset(self) -> None:
        """Instantly restore the database to seed snapshot without restarting process."""
        if self.url:
            try:
                res = httpx.post(f"{self.url}/api/reset", timeout=2.0)
                if res.status_code == 200:
                    return
            except Exception:
                pass

        if not self.runtime_db or not self.seed_db.exists():
            raise RuntimeError("Cannot reset world: runtime or seed DB not initialized")

        shutil.copyfile(self.seed_db, self.runtime_db)

    def stop(self) -> None:
        """Clean shutdown of background process and removal of temp files."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2.0)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

        if self.temp_dir and self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            except Exception:
                pass
            self.temp_dir = None

    def __enter__(self) -> World:
        return self.start()

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()
