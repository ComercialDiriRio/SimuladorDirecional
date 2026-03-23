# -*- coding: utf-8 -*-
"""Painel analytics (paridade com `client_analytics` no Streamlit)."""
from __future__ import annotations

from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends

from simulador_dv.api.data_context import get_simulador_context
from simulador_dv.api.deps import require_session_state
from simulador_dv.services.analytics_cliente import build_analytics_payload

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/cliente")
def get_analytics_cliente(
    st: Annotated[dict, Depends(require_session_state)],
) -> Dict[str, Any]:
    _, _, _, _, _, prem = get_simulador_context()
    dados = st.get("dados_cliente") or {}
    return build_analytics_payload(dados, prem)
