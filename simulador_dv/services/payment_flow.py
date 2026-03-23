# -*- coding: utf-8 -*-
"""Fechamento financeiro: gap, PS e parcela do financiamento (paridade Streamlit)."""
from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from simulador_dv.core.pro_soluto_comparador import metricas_pro_soluto, parcela_ps_para_valor
from simulador_dv.data.premissas import DEFAULT_PREMISSAS
from simulador_dv.services.financeiro import calcular_parcela_financiamento, taxa_fin_vigente


def _ps_max_unidade(
    df_estoque: pd.DataFrame, d: Dict[str, Any]
) -> float:
    if df_estoque is None or df_estoque.empty:
        return 0.0
    uid = d.get("unidade_id")
    emp = d.get("empreendimento_nome")
    if not uid or not emp:
        return 0.0
    row_u = df_estoque[
        (df_estoque["Identificador"] == uid)
        & (df_estoque["Empreendimento"] == emp)
    ]
    if row_u.empty:
        return 0.0
    row_u = row_u.iloc[0]
    pol = d.get("politica", "Direcional")
    rank = d.get("ranking", "DIAMANTE")
    if pol == "Emcash":
        return float(row_u.get("PS_EmCash", 0.0) or 0)
    col_rank = f"PS_{str(rank).title()}" if rank else "PS_Diamante"
    if str(rank) == "AÇO":
        col_rank = "PS_Aco"
    return float(row_u.get(col_rank, 0.0) or 0)


def compute_payment_snapshot(
    dados_cliente: Dict[str, Any],
    premissas: Optional[Dict[str, float]] = None,
    df_estoque: Optional[pd.DataFrame] = None,
    df_politicas: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Saldo gap, limites PS, mensalidade, parcela financiamento — espelha `payment_flow` no Streamlit.
    """
    d = dict(dados_cliente or {})
    prem = dict(DEFAULT_PREMISSAS)
    if premissas:
        prem.update({k: float(v) for k, v in premissas.items() if v is not None})

    u_valor = float(d.get("imovel_valor", 0) or 0)
    f_u = float(d.get("finan_usado", 0) or 0)
    fgts_u = float(d.get("fgts_sub_usado", 0) or 0)
    ps_atual = float(d.get("ps_usado", 0) or 0)
    prazo_finan = int(d.get("prazo_financiamento", 360) or 360)
    tab_fin = str(d.get("sistema_amortizacao", "SAC") or "SAC")

    r1 = float(d.get("ato_final", 0) or 0)
    r2 = float(d.get("ato_30", 0) or 0)
    r3 = float(d.get("ato_60", 0) or 0)
    r4 = float(d.get("ato_90", 0) or 0)
    vc_input = float(d.get("volta_caixa_ref", 0) or 0)
    if "volta_caixa_usado" in d:
        vc_input = float(d.get("volta_caixa_usado", 0) or 0)

    total_entrada_cash = r1 + r2 + r3 + r4
    gap_final = u_valor - f_u - fgts_u - ps_atual - total_entrada_cash - vc_input

    taxa = taxa_fin_vigente(d, prem)
    parcela_fin = calcular_parcela_financiamento(f_u, prazo_finan, taxa, tab_fin)

    ps_max_real = _ps_max_unidade(df_estoque, d)
    try:
        mps = metricas_pro_soluto(
            renda=float(d.get("renda", 0) or 0),
            valor_unidade=u_valor,
            politica_ui=str(d.get("politica", "Direcional")),
            ranking=str(d.get("ranking", "DIAMANTE")),
            premissas=prem,
            df_politicas=df_politicas,
            ps_cap_estoque=float(ps_max_real) if ps_max_real else None,
        )
    except Exception:
        mps = {
            "parcela_max_j8": 0.0,
            "parcela_max_g14": 0.0,
            "ps_max_efetivo": float(ps_max_real or 0),
            "ps_max_comparador_politica": 0.0,
            "cap_valor_unidade": 0.0,
            "prazo_ps_politica": int(d.get("prazo_ps_max", 60) or 60),
        }

    ps_limite_ui = float(mps.get("ps_max_efetivo", 0) or 0)
    prazo_cap_app = int(d.get("prazo_ps_max", 84) or 84)
    pol_prazo = int(mps.get("prazo_ps_politica", prazo_cap_app) or prazo_cap_app)
    parc_max_ui = max(1, min(pol_prazo, prazo_cap_app))

    parc = int(d.get("ps_parcelas", min(60, parc_max_ui)) or 1)
    parc = max(1, min(parc, parc_max_ui))
    v_parc = parcela_ps_para_valor(
        float(ps_atual or 0),
        parc,
        str(d.get("politica", "Direcional")),
        prem,
    )

    return {
        "gap_final": float(gap_final),
        "can_advance_summary": abs(gap_final) <= 1.0,
        "parcela_financiamento": float(parcela_fin),
        "taxa_financiamento_anual_pct": float(taxa),
        "entrada_total": float(total_entrada_cash),
        "saldo_para_atos": max(
            0.0, u_valor - f_u - fgts_u - ps_atual
        ),
        "ps_limite_ui": ps_limite_ui,
        "parc_max_ui": parc_max_ui,
        "pol_prazo": pol_prazo,
        "prazo_cap_app": prazo_cap_app,
        "ps_mensal": float(v_parc),
        "ps_mensal_simples": (float(ps_atual or 0) / parc) if parc > 0 else 0.0,
        "metricas_ps": {k: float(v) if isinstance(v, (int, float)) else v for k, v in mps.items()},
    }
