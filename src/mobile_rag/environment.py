"""Read local configuration without exposing secrets or changing process state."""

import os
from pathlib import Path

from dotenv import dotenv_values


def openrouter_api_key(project_root: Path | None = None) -> str | None:
    root = project_root or Path(__file__).resolve().parents[2]
    value = os.environ.get("OPENROUTER_API_KEY")
    if value and value.strip():
        return value.strip()
    for path in (root / ".env", root / "src/mobile_rag/.env"):
        value = dotenv_values(path, encoding="utf-8-sig", interpolate=False).get("OPENROUTER_API_KEY")
        if value and value.strip():
            return value.strip()
    return None
