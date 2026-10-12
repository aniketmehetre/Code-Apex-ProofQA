"""Shop twin launcher that copies seed.db and binds to a free port."""

import os
import shutil
import socket
import sys
import tempfile
from pathlib import Path

import uvicorn

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SEED_DB_PATH = Path(__file__).resolve().parent / "seed.db"


def find_free_port() -> int:
    """Bind to port 0 to let OS assign an open port, then release."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def run_twin(port: int | None = None, host: str = "127.0.0.1") -> None:
    # 1. Ensure seed.db exists
    if not SEED_DB_PATH.exists():
        from apps.shop_twin.backend.seed import seed_database
        seed_database(SEED_DB_PATH)

    # 2. Use existing SHOP_DB_PATH if set, else create fresh isolated copy
    if "SHOP_DB_PATH" not in os.environ or not os.environ["SHOP_DB_PATH"]:
        runtime_dir = Path(tempfile.mkdtemp(prefix="shop_twin_"))
        runtime_db = runtime_dir / "runtime.db"
        shutil.copyfile(SEED_DB_PATH, runtime_db)
        os.environ["SHOP_DB_PATH"] = str(runtime_db)
    else:
        runtime_db = Path(os.environ["SHOP_DB_PATH"])

    # 3. Determine port
    if port is None:
        env_port = os.environ.get("PORT")
        port = int(env_port) if env_port else find_free_port()

    print("=== Starting Shop Twin ===")
    print(f"URL: http://{host}:{port}")
    print(f"Database: {runtime_db}")
    print(f"Active Bugs: {os.environ.get('BUGS', 'NONE')}")

    uvicorn.run("apps.shop_twin.backend.app:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    cli_port = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_twin(port=cli_port)
