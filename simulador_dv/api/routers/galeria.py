# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from simulador_dv.api.deps import require_admin, require_session_state
from simulador_dv.services.galeria_catalogo import (
    aplicar_patch_galeria_admin,
    criar_empreendimento_galeria_admin,
    excluir_empreendimento_galeria_admin,
    lista_produtos_ordenada,
    load_catalogo_merged,
    metricas_empreendimento_estoque,
)
from simulador_dv.services.sistema_data import load_sistema_dataframes

router = APIRouter(prefix="/galeria", tags=["galeria"])


class GaleriaImagemIn(BaseModel):
    nome: str = ""
    link: str = ""


class GaleriaPatchIn(BaseModel):
    video: Optional[str] = None
    imagens: Optional[List[GaleriaImagemIn]] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class GaleriaCreateIn(BaseModel):
    nome: str = Field(..., min_length=1, description="Nome único do empreendimento na galeria")
    video: Optional[str] = ""
    imagens: Optional[List[GaleriaImagemIn]] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


@router.get("/catalogo")
def get_catalogo_galeria(
    st: dict = Depends(require_session_state),
) -> Dict[str, Any]:
    _ = st["_session_id"]
    cat = load_catalogo_merged()
    return {
        "produtos": lista_produtos_ordenada(cat),
        "catalogo": cat,
        "is_admin": bool(st.get("is_admin")),
    }


@router.patch("/produto/{nome:path}")
def patch_galeria_produto(
    nome: str,
    body: GaleriaPatchIn,
    st: Annotated[dict, Depends(require_admin)],
) -> Dict[str, Any]:
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=400, detail="Nada a atualizar (envie video, imagens, lat e/ou lon)")
    try:
        meta = aplicar_patch_galeria_admin(nome.strip(), patch)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"ok": True, "meta": meta}


@router.post("/produto")
def post_galeria_produto(
    body: GaleriaCreateIn,
    st: Annotated[dict, Depends(require_admin)],
) -> Dict[str, Any]:
    _ = st["_session_id"]
    payload = {
        "video": body.video or "",
        "imagens": [i.model_dump() for i in (body.imagens or [])],
        "lat": body.lat,
        "lon": body.lon,
    }
    try:
        meta = criar_empreendimento_galeria_admin(body.nome.strip(), payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "meta": meta}


@router.delete("/produto/{nome:path}")
def delete_galeria_produto(
    nome: str,
    st: Annotated[dict, Depends(require_admin)],
) -> Dict[str, Any]:
    _ = st["_session_id"]
    try:
        excluir_empreendimento_galeria_admin(nome.strip())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"ok": True}


@router.get("/empreendimento/{nome:path}")
def get_metricas_galeria(
    nome: str,
    st: Annotated[dict, Depends(require_session_state)],
) -> Dict[str, Any]:
    _ = st["_session_id"]
    cat = load_catalogo_merged()
    nome_dec = nome.strip()
    if nome_dec not in cat:
        raise HTTPException(status_code=404, detail="Empreendimento não está no catálogo da galeria")
    _, df_estoque, _, _, _, _, _ = load_sistema_dataframes()
    meta = cat[nome_dec]
    metricas = metricas_empreendimento_estoque(nome_dec, df_estoque)
    return {"meta": meta, "metricas_estoque": metricas}


@router.get("/metricas-batch")
def get_metricas_batch(
    produtos: str = "",
    st: dict = Depends(require_session_state),
) -> Dict[str, Any]:
    """Métricas de estoque para vários produtos num único pedido (menos round-trips)."""
    _ = st["_session_id"]
    cat = load_catalogo_merged()
    raw = [p.strip() for p in (produtos or "").split(",") if p.strip()]
    nomes = [n for n in raw if n in cat]
    if not nomes:
        return {"metricas_por_produto": {}}
    _, df_estoque, _, _, _, _, _ = load_sistema_dataframes()
    out: Dict[str, Any] = {}
    for n in nomes:
        out[n] = metricas_empreendimento_estoque(n, df_estoque)
    return {"metricas_por_produto": out}
