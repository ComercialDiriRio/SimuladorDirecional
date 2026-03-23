# -*- coding: utf-8 -*-
"""Lógica de `payment_flow` (gap, distribuição de atos, PS) alinhada ao Streamlit."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from simulador_dv.core.comparador_emcash import resolver_taxa_financiamento_anual_pct
from simulador_dv.core.pro_soluto_comparador import metricas_pro_soluto, parcela_ps_para_valor
from simulador_dv.data.premissas import DEFAULT_PREMISSAS
from simulador_dv.services.financeiro_streamlit import calcular_parcela_financiamento
from simulador_dv.services.motor_recomendacao import MotorRecomendacao


def ps_cap_max_estoque_row(d: Dict[str, Any], df_estoque: pd.DataFrame) -> float:
    if df_estoque.empty or not d.get("unidade_id") or not d.get("empreendimento_nome"):
        return 0.0
    row_u = df_estoque[
        (df_estoque["Identificador"] == d["unidade_id"]) & (df_estoque["Empreendimento"] == d["empreendimento_nome"])
    ]
    if row_u.empty:
        return 0.0
    row_u = row_u.iloc[0]
    pol = d.get("politica", "Direcional")
    rank = d.get("ranking", "DIAMANTE")
    if pol == "Emcash":
        return float(row_u.get("PS_EmCash", 0.0) or 0)
    col_rank = f"PS_{rank.title()}" if rank else "PS_Diamante"
    if rank == "AÇO":
        col_rank = "PS_Aco"
    return float(row_u.get(col_rank, 0.0) or 0)


def distribuir_restante(
    u_valor: float,
    f_u: float,
    fgts_u: float,
    ps_u: float,
    a1: float,
    n_parcelas: int,
) -> Tuple[float, float, float]:
    """
    Botões "Distribuir Restante em 2x / 3x" — retorna (ato_30, ato_60, ato_90).
    """
    gap_total = max(0.0, u_valor - f_u - fgts_u - ps_u)
    restante = max(0.0, gap_total - a1)
    if restante > 0 and n_parcelas > 0:
        val_per = restante / n_parcelas
        if n_parcelas == 2:
            return val_per, val_per, 0.0
        if n_parcelas == 3:
            return val_per, val_per, val_per
    return 0.0, 0.0, 0.0


def entrada_total(ato_final: float, ato_30: float, ato_60: float, ato_90: float) -> float:
    return float(ato_final) + float(ato_30) + float(ato_60) + float(ato_90)


def gap_final(
    u_valor: float,
    f_u: float,
    fgts_u: float,
    ps_u: float,
    ato_final: float,
    ato_30: float,
    ato_60: float,
    ato_90: float,
    volta_caixa: float,
) -> float:
    tot = entrada_total(ato_final, ato_30, ato_60, ato_90)
    return float(u_valor) - float(f_u) - float(fgts_u) - float(ps_u) - tot - float(volta_caixa)


def metricas_ps_pagamento(
    d: Dict[str, Any],
    u_valor: float,
    ps_max_real: float,
    df_politicas: pd.DataFrame,
    premissas: Dict[str, float],
) -> Dict[str, Any]:
    try:
        mps = metricas_pro_soluto(
            renda=float(d.get("renda", 0) or 0),
            valor_unidade=u_valor,
            politica_ui=str(d.get("politica", "Direcional")),
            ranking=str(d.get("ranking", "DIAMANTE")),
            premissas=premissas,
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
    return mps


def prazo_parcelas_limites(d: Dict[str, Any], mps: Dict[str, Any]) -> Tuple[int, int]:
    prazo_cap_app = int(d.get("prazo_ps_max", 84) or 84)
    pol_prazo = int(mps.get("prazo_ps_politica", prazo_cap_app) or prazo_cap_app)
    parc_max_ui = max(1, min(pol_prazo, prazo_cap_app))
    return parc_max_ui, pol_prazo


def mensalidade_ps(
    ps_valor: float,
    parc: int,
    politica: str,
    premissas: Dict[str, float],
) -> Tuple[float, float]:
    v_parc = parcela_ps_para_valor(float(ps_valor or 0), int(parc), str(politica), premissas)
    simples = (float(ps_valor or 0) / parc) if parc > 0 else 0.0
    return float(v_parc), float(simples)


def build_payment_context(
    dados_cliente: Dict[str, Any],
    df_estoque: pd.DataFrame,
    df_politicas: pd.DataFrame,
    premissas_dict: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Estado consolidado para o ecrã de pagamento (valores, PS, gap, parcela financiamento).
    """
    _prem = dict(DEFAULT_PREMISSAS)
    if premissas_dict:
        _prem.update(premissas_dict)

    d = dict(dados_cliente)
    u_valor = float(d.get("imovel_valor", 0) or 0)
    f_u = float(d.get("finan_usado", 0) or 0)
    fgts_u = float(d.get("fgts_sub_usado", 0) or 0)
    prazo_finan = int(d.get("prazo_financiamento", 360) or 360)
    tab_fin = d.get("sistema_amortizacao", "SAC")

    ps_u = float(d.get("ps_usado", 0) or 0)
    ato_f = float(d.get("ato_final", 0) or 0)
    ato30 = float(d.get("ato_30", 0) or 0)
    ato60 = float(d.get("ato_60", 0) or 0)
    ato90 = float(d.get("ato_90", 0) or 0)
    vc = float(d.get("volta_caixa_input", d.get("volta_caixa_key", 0)) or 0)

    ps_max = ps_cap_max_estoque_row(d, df_estoque)
    mps = metricas_ps_pagamento(d, u_valor, ps_max, df_politicas, _prem)
    parc_max, pol_prazo = prazo_parcelas_limites(d, mps)
    parc = int(d.get("ps_parcelas") or min(60, parc_max))
    parc = max(1, min(parc, parc_max))

    v_parc, ps_simples = mensalidade_ps(ps_u, parc, str(d.get("politica", "Direcional")), _prem)

    taxa = resolver_taxa_financiamento_anual_pct(d, _prem)
    parc_fin = calcular_parcela_financiamento(f_u, prazo_finan, taxa, tab_fin)
    g = gap_final(u_valor, f_u, fgts_u, ps_u, ato_f, ato30, ato60, ato90, vc)

    return {
        "resumo_unidade": {
            "empreendimento": d.get("empreendimento_nome", "N/A"),
            "unidade": d.get("unidade_id", "N/A"),
            "valor_final": u_valor,
            "financiamento": f_u,
            "fgts_sub": fgts_u,
            "prazo_fin": prazo_finan,
            "sistema": tab_fin,
        },
        "metricas_ps": mps,
        "ps_limite_ui": float(mps.get("ps_max_efetivo", 0) or 0),
        "parc_max_ui": parc_max,
        "pol_prazo": pol_prazo,
        "prazo_cap_app": int(d.get("prazo_ps_max", 84) or 84),
        "mensalidade_ps": v_parc,
        "ps_mensal_simples": ps_simples,
        "parcela_financiamento": parc_fin,
        "taxa_financiamento_anual_pct": taxa,
        "gap_final": g,
        "pode_avancar_resumo": abs(g) <= 1.0,
        "volta_caixa_ref": float(d.get("volta_caixa_ref", 0) or 0),
        "volta_caixa_aplicada": vc,
    }


def termometro_selection(
    d: Dict[str, Any],
    u_row: pd.Series,
    valor_para_termo: float,
    motor: MotorRecomendacao,
) -> Dict[str, float]:
    """Percentual do termômetro na etapa selection (igual ao Streamlit)."""
    fin_t = float(d.get("finan_usado", 0) or 0)
    sub_t = float(d.get("fgts_sub_usado", 0) or 0)
    pol = d.get("politica", "Direcional")
    rank = d.get("ranking", "DIAMANTE")
    if pol == "Emcash":
        ps_max_val = float(u_row.get("PS_EmCash", 0.0) or 0)
    else:
        col_rank = f"PS_{str(rank).title()}" if rank else "PS_Diamante"
        if rank == "AÇO":
            col_rank = "PS_Aco"
        ps_max_val = float(u_row.get(col_rank, 0.0) or 0)
    poder_t, _ = motor.calcular_poder_compra(float(d.get("renda", 0) or 0), fin_t, sub_t, ps_max_val)
    v_venda = float(valor_para_termo)
    pct = min(100, max(0, (poder_t / v_venda) * 100)) if v_venda > 0 else 0
    return {"poder_compra": float(poder_t), "percentual_cobertura": float(pct)}
