# -*- coding: utf-8 -*-
"""Busca em BD Clientes (lista principal); fallback BD Simulações se clientes vazio."""
from __future__ import annotations

import logging
from typing import Annotated, Any, Dict, List

import pandas as pd
from fastapi import APIRouter, Depends, Query

from simulador_dv.api.data_context import get_simulador_context
from simulador_dv.api.deps import require_session_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cadastros", tags=["cadastros"])


@router.get("/buscar")
def get_buscar_cadastros(
    st: Annotated[dict, Depends(require_session_state)],
    q: str = Query("", description="Texto no nome ou CPF"),
    limite: int = Query(50, ge=1, le=200),
) -> Dict[str, Any]:
    _ = st["_session_id"]
    _, _, _, df_clientes, df_simulacoes, _ = get_simulador_context()
    df = df_clientes if df_clientes is not None and not df_clientes.empty else df_simulacoes
    if df is None or df.empty:
        logger.warning("Busca cadastros: sem BD Clientes nem BD Simulações")
        return {"itens": [], "total": 0, "fonte": "vazio"}
    df = df.copy()
    fonte = "bd_clientes" if df_clientes is not None and not df_clientes.empty else "bd_simulacoes"
    logger.info("Busca cadastros: fonte=%s, %d registros, q=%r", fonte, len(df), q)
    col_nome = "Nome" if "Nome" in df.columns else None
    col_cpf = "CPF" if "CPF" in df.columns else None
    term = q.strip()
    if term:
        mask = pd.Series(False, index=df.index)
        if col_nome:
            mask = mask | df[col_nome].astype(str).str.contains(term, case=False, na=False)
        if col_cpf:
            mask = mask | df[col_cpf].astype(str).str.contains(term, case=False, na=False)
        df = df[mask]
    df = df.head(limite)
    recs: List[Dict[str, Any]] = df.astype(object).where(pd.notnull(df), None).to_dict(orient="records")
    return {"itens": recs, "total": len(recs), "fonte": fonte}


@router.get("/buscar-simulacoes")
def get_buscar_simulacoes(
    st: Annotated[dict, Depends(require_session_state)],
    q: str = Query("", description="Nome ou CPF"),
    limite: int = Query(50, ge=1, le=200),
) -> Dict[str, Any]:
    """Lista linhas de BD Simulações (reabrir simulação exata pelo histórico)."""
    _ = st["_session_id"]
    _, _, _, _, df_simulacoes, _ = get_simulador_context()
    if df_simulacoes is None or df_simulacoes.empty:
        return {"itens": [], "total": 0}
    df = df_simulacoes.copy()
    col_nome = "Nome" if "Nome" in df.columns else None
    col_cpf = "CPF" if "CPF" in df.columns else None
    term = q.strip()
    if term:
        mask = pd.Series(False, index=df.index)
        if col_nome:
            mask = mask | df[col_nome].astype(str).str.contains(term, case=False, na=False)
        if col_cpf:
            mask = mask | df[col_cpf].astype(str).str.contains(term, case=False, na=False)
        df = df[mask]
    df = df.head(limite)
    recs: List[Dict[str, Any]] = df.astype(object).where(pd.notnull(df), None).to_dict(orient="records")
    return {"itens": recs, "total": len(recs)}
