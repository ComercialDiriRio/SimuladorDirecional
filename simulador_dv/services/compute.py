# -*- coding: utf-8 -*-
"""Cálculos expostos à API (sem Streamlit)."""
from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from simulador_dv.core.pro_soluto_comparador import metricas_pro_soluto, parcela_ps_para_valor
from simulador_dv.data.premissas import DEFAULT_PREMISSAS


def compute_metricas_ps(
    dados_cliente: Dict[str, Any],
    premissas: Optional[Dict[str, float]] = None,
    df_politicas: Optional[pd.DataFrame] = None,
    ps_cap_estoque: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Retorna métricas Pro Soluto alinhadas a `metricas_pro_soluto` (fechamento).
    """
    dc = dados_cliente or {}
    renda = float(dc.get("renda") or 0)
    vu = float(dc.get("imovel_valor") or 0)
    politica = str(dc.get("politica") or "Direcional")
    ranking = str(dc.get("ranking") or "DIAMANTE")
    prem = dict(DEFAULT_PREMISSAS)
    if premissas:
        prem.update({k: float(v) for k, v in premissas.items() if v is not None})

    cap = ps_cap_estoque
    if cap is None and dc.get("ps_cap_estoque") is not None:
        cap = float(dc["ps_cap_estoque"])

    m = metricas_pro_soluto(
        renda=renda,
        valor_unidade=vu,
        politica_ui=politica,
        ranking=ranking,
        premissas=prem,
        df_politicas=df_politicas,
        ps_cap_estoque=cap,
    )
    prazo = int(dc.get("ps_parcelas") or m.get("prazo_ps_politica") or 84)
    ps_val = float(dc.get("ps_usado") or 0)
    mensalidade = parcela_ps_para_valor(ps_val, prazo, politica, prem)

    return {
        "parcela_max_g14": float(m.get("parcela_max_g14") or 0),
        "parcela_max_j8": float(m.get("parcela_max_j8") or 0),
        "ps_max_efetivo": float(m.get("ps_max_efetivo") or 0),
        "ps_max_comparador_politica": float(m.get("ps_max_comparador_politica") or 0),
        "cap_valor_unidade": float(m.get("cap_valor_unidade") or 0),
        "prazo_ps_politica": int(m.get("prazo_ps_politica") or 84),
        "k3": float(m.get("k3") or 0),
        "e1": float(m.get("e1") or 0),
        "mensalidade_ps": float(mensalidade),
    }
