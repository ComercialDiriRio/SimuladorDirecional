# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Annotated, Any, Dict

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from simulador_dv.api.data_context import get_simulador_context
from simulador_dv.api.deps import require_session_state
from simulador_dv.api.estado_helpers import estado_sessao_out
from simulador_dv.api.schemas_flow import (
    ClienteAtivarCpfIn,
    ClienteConfirmarIn,
    ClienteIn,
    EstadoSessaoOut,
    HistoricoImportIn,
)
from simulador_dv.services.cliente_merge import merge_cliente_base_com_ultima_simulacao
from simulador_dv.services.cpf_utils import limpar_cpf_visual
from simulador_dv.api.session_store import update_session
from simulador_dv.services.cliente_cadastro import confirmar_cadastro
from simulador_dv.services.historico_import import build_dados_cliente_from_historico_row

router = APIRouter(prefix="/cliente", tags=["cliente"])


@router.put("", response_model=EstadoSessaoOut)
def put_cliente(
    body: ClienteIn,
    st: Annotated[dict, Depends(require_session_state)],
) -> EstadoSessaoOut:
    sid = st["_session_id"]
    raw = body.model_dump(exclude_unset=True)
    extra = raw.pop("extra", None) or {}
    merge = {k: v for k, v in raw.items() if v is not None}
    merge.update(extra)
    updated = update_session(sid, {"dados_cliente": merge})
    assert updated is not None
    return estado_sessao_out(updated)


@router.post("/confirmar", response_model=EstadoSessaoOut)
def post_confirmar_cadastro(
    body: ClienteConfirmarIn,
    st: Annotated[dict, Depends(require_session_state)],
) -> EstadoSessaoOut:
    """Espelha submit do `form_cadastro` + validações do Streamlit."""
    sid = st["_session_id"]
    motor, _, _, _, _, _ = get_simulador_context()
    rendas = list(body.rendas_lista or [])
    while len(rendas) < body.qtd_participantes:
        rendas.append(0.0)
    rendas = rendas[:4]

    delta, err = confirmar_cadastro(
        nome=body.nome,
        cpf_val=body.cpf,
        data_nascimento=body.data_nascimento,
        rendas_lista=rendas,
        qtd_participantes=body.qtd_participantes,
        ranking=body.ranking,
        politica_ps=body.politica,
        social=body.social,
        cotista=body.cotista,
        motor=motor,
    )
    if err:
        raise HTTPException(status_code=400, detail=err)
    assert delta is not None
    updated = update_session(
        sid,
        {
            "dados_cliente": delta,
            "cliente_ativo": True,
        },
    )
    assert updated is not None
    return estado_sessao_out(updated)


@router.post("/ativar-por-cpf", response_model=EstadoSessaoOut)
def post_ativar_por_cpf(
    body: ClienteAtivarCpfIn,
    st: Annotated[dict, Depends(require_session_state)],
) -> EstadoSessaoOut:
    """BD Clientes + merge da última simulação (BD Simulações) para o mesmo CPF."""
    sid = st["_session_id"]
    _, _, _, df_clientes, df_simulacoes, _ = get_simulador_context()
    if df_clientes is None or df_clientes.empty:
        raise HTTPException(
            status_code=503,
            detail="BD Clientes indisponível ou vazia. Use importar histórico a partir de BD Simulações.",
        )
    cpf_n = limpar_cpf_visual(body.cpf)
    if len(cpf_n) < 11:
        raise HTTPException(status_code=400, detail="CPF inválido.")
    sub = df_clientes[df_clientes["CPF"].apply(limpar_cpf_visual) == cpf_n]
    if sub.empty:
        raise HTTPException(status_code=404, detail="Cliente não encontrado em BD Clientes.")
    row = sub.iloc[0].astype(object).where(pd.notnull(sub.iloc[0]), None).to_dict()
    dc = merge_cliente_base_com_ultima_simulacao(row, df_simulacoes if df_simulacoes is not None else pd.DataFrame())
    if dc.get("finan_f_ref") in (None, 0) and dc.get("sub_f_ref") in (None, 0):
        motor, _, _, _, _, _ = get_simulador_context()
        f_ref, s_ref, _ = motor.obter_enquadramento(
            float(dc.get("renda", 0) or 0),
            bool(dc.get("social")),
            bool(dc.get("cotista")),
            valor_avaliacao=240000,
        )
        dc["finan_f_ref"] = f_ref
        dc["sub_f_ref"] = s_ref
    updated = update_session(
        sid,
        {
            "dados_cliente": dc,
            "cliente_ativo": True,
            "passo_simulacao": "input",
        },
    )
    assert updated is not None
    return estado_sessao_out(updated)


@router.post("/importar-historico", response_model=EstadoSessaoOut)
def post_importar_historico(
    body: HistoricoImportIn,
    st: Annotated[dict, Depends(require_session_state)],
) -> EstadoSessaoOut:
    """Reconstrói sessão a partir de uma linha de BD Simulações (sidebar Streamlit)."""
    sid = st["_session_id"]
    dc = build_dados_cliente_from_historico_row(body.row)
    updated = update_session(
        sid,
        {
            "dados_cliente": dc,
            "cliente_ativo": True,
            "passo_simulacao": "fechamento_aprovado",
        },
    )
    assert updated is not None
    return estado_sessao_out(updated)
