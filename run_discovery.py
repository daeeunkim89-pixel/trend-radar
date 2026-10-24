"""Run public discovery with checked dependencies; never send Telegram."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent
IMPORT_CHECK = "import requests, bs4, lxml, cryptography"


def ready(python):
    result = subprocess.run([str(python), "-c", IMPORT_CHECK],
                            capture_output=True, text=True, timeout=15)
    return result.returncode == 0


def runtime(root=ROOT):
    if ready(sys.executable):
        return Path(sys.executable)
    envdir = root / "work" / "collector-runtime"
    python = envdir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(envdir)
    if not ready(python):
        print("BTP DISCOVERY SETUP: installing collector dependencies before collection", flush=True)
        result = subprocess.run(
            [str(python), "-m", "pip", "install", "--disable-pip-version-check",
             "--no-input", "--retries", "0", "--timeout", "10", "-r", str(root / "requirements.txt")],
            capture_output=True, text=True, timeout=90)
        if result.returncode:
            raise RuntimeError("Collector dependency installation failed; no collection was attempted")
        if not ready(python):
            raise RuntimeError("Collector dependencies still unavailable after installation")
    return python


def run(min_refresh_seconds=0, root=ROOT):
    try:
        python = runtime(root)
        child_env = os.environ.copy()
        for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "EXPECTED_TELEGRAM_CHAT_SHA256"):
            child_env.pop(key, None)
        result = subprocess.run(
            [str(python), "-u", str(root / "candidate_snapshot.py"),
             "--min-refresh-seconds", str(min_refresh_seconds)],
            cwd=root, env=child_env, timeout=120)
        return result.returncode
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        # Environment/setup failures are never reported as a successful empty collection.
        print("BTP DISCOVERY ENVIRONMENT FAILED:", type(error).__name__, str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-refresh-seconds", type=int, default=0)
    args = parser.parse_args()
    if args.min_refresh_seconds < 0:
        parser.error("Refresh interval cannot be negative")
    raise SystemExit(run(args.min_refresh_seconds))
