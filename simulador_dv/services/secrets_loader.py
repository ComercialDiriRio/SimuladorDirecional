# -*- coding: utf-8 -*-
"""Lê `.streamlit/secrets.toml` na raiz do projeto (API sem Streamlit)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]


def load_secrets_toml() -> Dict[str, Any]:
    path = ROOT / ".streamlit" / "secrets.toml"
    if not path.is_file():
        return {}
    try:
        import tomllib

        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}
