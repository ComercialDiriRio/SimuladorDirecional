# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Annotated, Any, Dict, Optional

from fastapi import APIRouter, Body, Depends

from simulador_dv.api.deps import require_session_state
from simulador_dv.api.schemas_flow import RecomendacoesIn
from simulador_dv.services.recomendacoes_guide import build_guide_payload
from simulador_dv.services.sistema_data import load_sistema_dataframes

router = APIRouter(prefix="/simulacao", tags=["simulacao"])


@router.post("/recomendacoes")
def post_recomendacoes(
    st: Annotated[dict, Depends(require_session_state)],
    body: Optional[RecomendacoesIn] = Body(default=None),
) -> Dict[str, Any]:
    _ = st["_session_id"]
    dados = st.get("dados_cliente") or {}
    _, df_estoque, _, _, _, _, _ = load_sistema_dataframes()
    emp = (body.empreendimento if body else None) or None
    filt = None if emp in (None, "", "Todos") else emp
    return build_guide_payload(df_estoque, dados, empreendimento_filtro=filt)
