# -*- coding: utf-8 -*-
"""CRUD para Campanhas Comerciais e Treinamentos (armazenamento em JSON local)."""
from __future__ import annotations

import copy
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from simulador_dv.api.deps import require_admin, require_session_state
from simulador_dv.services.home_banners import cms_content_cache_ttl_sec

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conteudo", tags=["conteudo"])

_JSON_PATH = Path(__file__).resolve().parents[2] / "data" / "conteudo.json"

_conteudo_cache_t: float = 0.0
_conteudo_cache_payload: Optional[Dict[str, List[Dict[str, Any]]]] = None


def _invalidate_conteudo_data_cache() -> None:
    global _conteudo_cache_t, _conteudo_cache_payload
    _conteudo_cache_t = 0.0
    _conteudo_cache_payload = None


def _load_data_uncached() -> Dict[str, List[Dict[str, Any]]]:
    try:
        from simulador_dv.services import sheets_cms

        sheet = sheets_cms.conteudo_from_sheet()
        if sheet and (sheet.get("campanhas") or sheet.get("treinamentos")):
            return {
                "campanhas": list(sheet.get("campanhas") or []),
                "treinamentos": list(sheet.get("treinamentos") or []),
            }
    except Exception as e:
        logger.debug("conteudo_from_sheet: %s", e)
    if _JSON_PATH.is_file():
        with open(_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"campanhas": [], "treinamentos": []}


def _load_data() -> Dict[str, List[Dict[str, Any]]]:
    global _conteudo_cache_t, _conteudo_cache_payload
    now = time.monotonic()
    if _conteudo_cache_payload is not None and (now - _conteudo_cache_t) < cms_content_cache_ttl_sec():
        return copy.deepcopy(_conteudo_cache_payload)
    data = _load_data_uncached()
    _conteudo_cache_payload = copy.deepcopy(data)
    _conteudo_cache_t = now
    return copy.deepcopy(data)


def _save_data(data: Dict[str, List[Dict[str, Any]]]) -> None:
    _invalidate_conteudo_data_cache()
    _JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    try:
        from simulador_dv.services import sheets_cms

        sheets_cms.conteudo_save_full(data)
    except Exception as e:
        logger.debug("conteudo_save_full: %s", e)


class MediaItem(BaseModel):
    titulo: str = ""
    url: str = ""


class ConteudoIn(BaseModel):
    titulo: str
    descricao: str = ""
    imagem: str = ""
    data: str = ""
    video_url: str = ""
    imagens_drive: List[MediaItem] = Field(default_factory=list)
    pdfs: List[MediaItem] = Field(default_factory=list)


# --- Campanhas ---

@router.get("/campanhas")
def get_campanhas(st: Annotated[dict, Depends(require_session_state)]) -> Dict[str, Any]:
    data = _load_data()
    return {"campanhas": data.get("campanhas", []), "is_admin": bool(st.get("is_admin"))}


@router.post("/campanhas")
def post_campanha(body: ConteudoIn, st: Annotated[dict, Depends(require_admin)]) -> Dict[str, Any]:
    data = _load_data()
    item = {"id": f"camp-{uuid.uuid4().hex[:8]}", **body.model_dump()}
    data.setdefault("campanhas", []).append(item)
    _save_data(data)
    return {"ok": True, "item": item}


@router.patch("/campanhas/{item_id}")
def patch_campanha(
    item_id: str, body: ConteudoIn, st: Annotated[dict, Depends(require_admin)]
) -> Dict[str, Any]:
    data = _load_data()
    lista = data.get("campanhas", [])
    for i, c in enumerate(lista):
        if c.get("id") == item_id:
            merged = {**c, **body.model_dump(), "id": item_id}
            lista[i] = merged
            data["campanhas"] = lista
            _save_data(data)
            return {"ok": True, "item": merged}
    raise HTTPException(status_code=404, detail="Campanha não encontrada")


@router.delete("/campanhas/{item_id}")
def delete_campanha(item_id: str, st: Annotated[dict, Depends(require_admin)]) -> Dict[str, Any]:
    data = _load_data()
    before = len(data.get("campanhas", []))
    data["campanhas"] = [c for c in data.get("campanhas", []) if c.get("id") != item_id]
    _save_data(data)
    removed = before - len(data["campanhas"])
    return {"ok": True, "removed": removed}


# --- Treinamentos ---

@router.get("/treinamentos")
def get_treinamentos(st: Annotated[dict, Depends(require_session_state)]) -> Dict[str, Any]:
    data = _load_data()
    return {"treinamentos": data.get("treinamentos", []), "is_admin": bool(st.get("is_admin"))}


@router.post("/treinamentos")
def post_treinamento(body: ConteudoIn, st: Annotated[dict, Depends(require_admin)]) -> Dict[str, Any]:
    data = _load_data()
    item = {"id": f"trein-{uuid.uuid4().hex[:8]}", **body.model_dump()}
    data.setdefault("treinamentos", []).append(item)
    _save_data(data)
    return {"ok": True, "item": item}


@router.patch("/treinamentos/{item_id}")
def patch_treinamento(
    item_id: str, body: ConteudoIn, st: Annotated[dict, Depends(require_admin)]
) -> Dict[str, Any]:
    data = _load_data()
    lista = data.get("treinamentos", [])
    for i, c in enumerate(lista):
        if c.get("id") == item_id:
            merged = {**c, **body.model_dump(), "id": item_id}
            lista[i] = merged
            data["treinamentos"] = lista
            _save_data(data)
            return {"ok": True, "item": merged}
    raise HTTPException(status_code=404, detail="Treinamento não encontrado")


@router.delete("/treinamentos/{item_id}")
def delete_treinamento(item_id: str, st: Annotated[dict, Depends(require_admin)]) -> Dict[str, Any]:
    data = _load_data()
    before = len(data.get("treinamentos", []))
    data["treinamentos"] = [t for t in data.get("treinamentos", []) if t.get("id") != item_id]
    _save_data(data)
    removed = before - len(data["treinamentos"])
    return {"ok": True, "removed": removed}
