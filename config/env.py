"""Load local environment configuration from a ``.env`` file.

The application reads credentials (Dhan, Supabase, ...) from ``os.environ``.
Nothing used to populate ``os.environ`` from a ``.env`` file, so credentials kept
there were silently ignored and provider calls failed with "missing configuration".
Call :func:`load_environment` once at every entry point (Streamlit, API, CLI).
"""

from __future__ import annotations

from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_loaded = False


def load_environment(dotenv_path: Path | str | None = None) -> bool:
    """Load ``.env`` into ``os.environ`` without overriding real environment variables.

    Returns True when a file was found and loaded. Safe to call repeatedly, and a
    no-op when python-dotenv is not installed or no ``.env`` file exists.
    """
    global _loaded
    if _loaded and dotenv_path is None:
        return True
    try:
        from dotenv import load_dotenv
    except ImportError:
        return False

    path = Path(dotenv_path) if dotenv_path is not None else _PROJECT_ROOT / ".env"
    if not path.is_file():
        return False
    loaded = bool(load_dotenv(path, override=False))
    if dotenv_path is None:
        _loaded = loaded
    return loaded
