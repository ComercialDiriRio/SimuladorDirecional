# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends, Query

from simulador_dv.api.data_context import get_simulador_context
from simulador_dv.api.deps import require_session_state
from simulador_dv.api.estado_helpers import estado_sessao_out
from simulador_dv.api.schemas_flow import EstadoSessaoOut, FechamentoIn
from simulador_dv.api.session_store import update_session
from simulador_dv.services.fechamento_ui import build_fechamento_context, arredondar_para_curva

router = APIRouter(prefix="/fechamento", tags=["fechamento"])


@router.get("/contexto")
def get_fechamento_contexto(
    st: Annotated[dict, Depends(require_session_state)],
) -> Dict[str, Any]:
    """Referências da curva + comparativo SAC/PRICE (sem alterar sessão)."""
    motor, _, _, _, _, prem = get_simulador_context()
    dados = st.get("dados_cliente") or {}
    return build_fechamento_context(dados, motor, prem)


@router.get("/arredondar")
def get_arredondar_curva(
    st: Annotated[dict, Depends(require_session_state)],
    valor: float = Query(..., description="Valor digitado pelo corretor"),
) -> Dict[str, Any]:
    """Arredonda valor de financiamento para o mais próximo na curva."""
    motor, _, _, _, _, _ = get_simulador_context()
    dc = st.get("dados_cliente") or {}
    renda = float(dc.get("renda", 0) or 0)
    social = bool(dc.get("social", False))
    cotista = bool(dc.get("cotista", True))
    resultado = arredondar_para_curva(valor, motor, renda, social, cotista)
    return {"valor_original": valor, "valor_arredondado": resultado or valor}


@router.put("", response_model=EstadoSessaoOut)
def put_fechamento(
    body: FechamentoIn,
    st: Annotated[dict, Depends(require_session_state)],
) -> EstadoSessaoOut:
    sid = st["_session_id"]
    patch_dc = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    updated = update_session(sid, {"dados_cliente": patch_dc})
    assert updated is not None
    return estado_sessao_out(updated)
