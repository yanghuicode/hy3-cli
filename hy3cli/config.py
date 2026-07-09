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
        # Default endpoint/model below are the real RhinoBird 2026 submission
        # values. Override via .env / environment if you have a different Hy3
        # deployment.
        "base_url": os.environ.get("HY3_BASE_URL",
                                   "http://101.43.51.108:3000/v1").rstrip("/"),
        "api_key": api_key,
        "model": os.environ.get("HY3_MODEL", "hunyuan-3.0-free"),
        "mock": mock,
        "os_hint": os.environ.get("HY3_OS", _detect_os()),
        "temperature": float(os.environ.get("HY3_TEMPERATURE", "0.2")),
        # hunyuan-3.0-free is a reasoning model: it spends a large share of the
        # token budget "thinking" before emitting the final JSON. A generous
        # budget is required so the answer is not truncated by max_tokens.
        "max_tokens": int(os.environ.get("HY3_MAX_TOKENS", "4096")),
        "timeout": int(os.environ.get("HY3_TIMEOUT", "120")),
        # The public RhinoBird endpoint can be intermittently flaky; retry
        # transient network / 5xx errors a few times with backoff.
        "retries": int(os.environ.get("HY3_RETRIES", "3")),
        "history_file": os.environ.get(
            "HY3_HISTORY", str(Path(os.path.expanduser("~")) / ".hy3cli" / "history.jsonl")
        ),
    }
