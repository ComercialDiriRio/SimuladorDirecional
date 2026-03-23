# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Annotated, Any, Dict, List

from fastapi import APIRouter, Depends

from simulador_dv.api.data_context import get_simulador_context
from simulador_dv.api.deps import require_session_state
from simulador_dv.api.schemas_flow import DistribuirAtosIn, PagamentoEstadoIn, PagamentoSimIn
from simulador_dv.api.session_store import get_session, update_session
from simulador_dv.services.pagamento_fluxo import calcular_fluxo_pagamento_detalhado
from simulador_dv.services.pagamento_ui import build_payment_context, distribuir_restante, gap_final

router = APIRouter(prefix="/pagamento", tags=["pagamento"])


def _contexto_por_sid(sid: str) -> Dict[str, Any]:
    _, df_estoque, df_politicas, _, _, prem = get_simulador_context()
    st = get_session(sid) or {}
    dados = st.get("dados_cliente") or {}
    return build_payment_context(dados, df_estoque, df_politicas, prem)


@router.get("/contexto")
def get_pagamento_contexto(
    st: Annotated[dict, Depends(require_session_state)],
) -> Dict[str, Any]:
    return _contexto_por_sid(st["_session_id"])


@router.patch("/estado")
def patch_pagamento_estado(
    body: PagamentoEstadoIn,
    st: Annotated[dict, Depends(require_session_state)],
) -> Dict[str, Any]:
    """Atualiza PS, parcelas, atos e volta ao caixa na sessão."""
    sid = st["_session_id"]
    patch = body.model_dump(exclude_unset=True)
    dc = {}
    if "ps_usado" in patch:
        dc["ps_usado"] = patch["ps_usado"]
    if "ps_parcelas" in patch:
        dc["ps_parcelas"] = patch["ps_parcelas"]
    if "ato_final" in patch:
        dc["ato_final"] = patch["ato_final"]
    if "ato_30" in patch:
        dc["ato_30"] = patch["ato_30"]
    if "ato_60" in patch:
        dc["ato_60"] = patch["ato_60"]
    if "ato_90" in patch:
        dc["ato_90"] = patch["ato_90"]
    if "volta_caixa" in patch:
        dc["volta_caixa_input"] = patch["volta_caixa"]
    update_session(sid, {"dados_cliente": dc})
    return _contexto_por_sid(sid)


@router.post("/distribuir")
def post_distribuir_atos(
    body: DistribuirAtosIn,
    st: Annotated[dict, Depends(require_session_state)],
) -> Dict[str, Any]:
    """Botões 2x / 3x do Streamlit."""
    sid = st["_session_id"]
    d = {**(st.get("dados_cliente") or {})}
    u_valor = float(d.get("imovel_valor", 0) or 0)
    f_u = float(d.get("finan_usado", 0) or 0)
    fgts_u = float(d.get("fgts_sub_usado", 0) or 0)
    ps_u = float(d.get("ps_usado", 0) or 0)
    a1 = float(d.get("ato_final", 0) or 0)
    ato30, ato60, ato90 = distribuir_restante(u_valor, f_u, fgts_u, ps_u, a1, body.n_parcelas)
    update_session(
        sid,
        {
            "dados_cliente": {
                "ato_30": ato30,
                "ato_60": ato60,
                "ato_90": ato90,
            }
        },
    )
    return _contexto_por_sid(sid)


@router.post("/simular")
def post_simular_pagamento(
    body: PagamentoSimIn,
    st: Annotated[dict, Depends(require_session_state)],
) -> Dict[str, Any]:
    _ = st["_session_id"]
    atos = {
        "ato_final": body.ato_final,
        "ato_30": body.ato_30,
        "ato_60": body.ato_60,
        "ato_90": body.ato_90,
    }
    df = calcular_fluxo_pagamento_detalhado(
        body.valor_financiado,
        body.meses_fin,
        body.taxa_anual,
        body.sistema,
        body.ps_mensal,
        body.meses_ps,
        atos,
    )
    fluxo: List[Dict[str, Any]] = df.astype(object).where(df.notnull(), None).to_dict(orient="records")
    return {"fluxo": fluxo, "linhas": len(fluxo)}


@router.get("/gap")
def get_gap(
    st: Annotated[dict, Depends(require_session_state)],
) -> Dict[str, Any]:
    sid = st["_session_id"]
    d = (get_session(sid) or {}).get("dados_cliente") or {}
    u_valor = float(d.get("imovel_valor", 0) or 0)
    f_u = float(d.get("finan_usado", 0) or 0)
    fgts_u = float(d.get("fgts_sub_usado", 0) or 0)
    ps_u = float(d.get("ps_usado", 0) or 0)
    vc = float(d.get("volta_caixa_input", 0) or 0)
    g = gap_final(
        u_valor,
        f_u,
        fgts_u,
        ps_u,
        float(d.get("ato_final", 0) or 0),
        float(d.get("ato_30", 0) or 0),
        float(d.get("ato_60", 0) or 0),
        float(d.get("ato_90", 0) or 0),
        vc,
    )
    return {"gap_final": g, "pode_avancar_resumo": abs(g) <= 1.0}
