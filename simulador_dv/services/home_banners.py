# -*- coding: utf-8 -*-
"""Banners da página inicial (overrides gravados em disco)."""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_home_banners_cache: Optional[Tuple[float, List[str]]] = None


def _cms_cache_ttl_sec() -> float:
    try:
        return max(15.0, float(os.environ.get("SIMULADOR_CMS_CACHE_TTL_SEC", "120")))
    except (TypeError, ValueError):
        return 120.0


def cms_content_cache_ttl_sec() -> float:
    """TTL partilhado por banners, catálogo galeria e conteúdo (env SIMULADOR_CMS_CACHE_TTL_SEC)."""
    return _cms_cache_ttl_sec()


def invalidate_home_banners_cache() -> None:
    global _home_banners_cache
    _home_banners_cache = None

_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "home_banners.json"

DEFAULT_BANNER_URLS: List[str] = [
    "https://images.unsplash.com/photo-1560518883-ce09059eeffa?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&q=80",
    "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&q=80",
    "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&q=80",
]


def _load_home_banners_from_file() -> Optional[List[str]]:
    if not _DATA_PATH.is_file():
        return None
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("imagens"), list):
            urls = [str(u).strip() for u in data["imagens"] if str(u).strip()]
            return urls if urls else None
    except Exception as e:
        logger.warning("home_banners: %s", e)
    return None


def load_home_banners() -> List[str]:
    """Lista de URLs (ordem = carrossel). Tenta aba «BD Home»; senão `home_banners.json`; senão defaults."""
    try:
        from simulador_dv.services import sheets_cms

        u = sheets_cms.home_banners_from_sheet()
        if u:
            return u
    except Exception as e:
        logger.debug("home_banners sheet: %s", e)
    file_urls = _load_home_banners_from_file()
    if file_urls:
        return file_urls
    return list(DEFAULT_BANNER_URLS)


def save_home_banners(urls: List[str]) -> List[str]:
    """Substitui a lista de banners (ficheiro local + aba «BD Home» se existir)."""
    invalidate_home_banners_cache()
    limpa = [str(u).strip() for u in urls if str(u).strip()]
    if not limpa:
        limpa = list(DEFAULT_BANNER_URLS)
    _DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload: Dict[str, Any] = {"imagens": limpa}
    with open(_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    try:
        from simulador_dv.services import sheets_cms

        sheets_cms.home_banners_save_sheet(limpa)
    except Exception as e:
        logger.debug("home_banners_save_sheet: %s", e)
    return limpa
