"""Hy3-CLI — a vibe-coded terminal command assistant powered by Hy3.

Configuration layer: load .env (no external dependency) and expose a single
get_config() that the rest of the app reads from.
"""
import os
import platform
from pathlib import Path


def _detect_os() -> str:
    """Return a shell/OS hint understood by Hy3."""
    sys = platform.system()
    if sys == "Windows":
        # Detect WSL for better command suggestions
        if "microsoft" in platform.release().lower():
            return "linux"
        return "windows"
    if sys == "Darwin":
        return "macos"
    return "linux"


def load_dotenv(path: str | None = None) -> None:
    """Minimal .env loader. Values already set in the environment win."""
    p = Path(path) if path else (Path(os.getcwd()) / ".env")
    if not p.exists():
        return
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def get_config() -> dict:
    load_dotenv()
    api_key = os.environ.get("HY3_API_KEY", "")
    mock = os.environ.get("HY3_MOCK", "0") == "1" or not api_key
    return {
        "base_url": os.environ.get("HY3_BASE_URL",
                                   "https://api.hunyuan.cloud.tencent.com/v1").rstrip("/"),
        "api_key": api_key,
        "model": os.environ.get("HY3_MODEL", "hy3"),
        "mock": mock,
        "os_hint": os.environ.get("HY3_OS", _detect_os()),
        "temperature": float(os.environ.get("HY3_TEMPERATURE", "0.2")),
        "timeout": int(os.environ.get("HY3_TIMEOUT", "60")),
        "history_file": os.environ.get(
            "HY3_HISTORY", str(Path(os.path.expanduser("~")) / ".hy3cli" / "history.jsonl")
        ),
    }
