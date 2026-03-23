# -*- coding: utf-8 -*-
"""Contexto de fechamento (2ª aba) alinhado ao Streamlit em `fechamento_aprovado`."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

import pandas as pd

from simulador_dv.core.comparador_emcash import resolver_taxa_financiamento_anual_pct
from simulador_dv.data.premissas import DEFAULT_PREMISSAS
from simulador_dv.services.financeiro_streamlit import calcular_comparativo_sac_price
from simulador_dv.services.motor_recomendacao import MotorRecomendacao

logger = logging.getLogger(__name__)


def atualizar_refs_curva(
    dados_cliente: Dict[str, Any],
    motor: MotorRecomendacao,
    valor_avaliacao: float = 240000.0,
) -> Tuple[float, float]:
    renda_cli = float(dados_cliente.get("renda", 0) or 0)
    social_cli = bool(dados_cliente.get("social", False))
    cotista_cli = bool(dados_cliente.get("cotista", True))
    f_curva, s_curva, _ = motor.obter_enquadramento(renda_cli, social_cli, cotista_cli, valor_avaliacao=valor_avaliacao)
    return float(f_curva), float(s_curva)


def aplicar_defaults_fechamento(dados: Dict[str, Any], f_curva: float, s_curva: float) -> Dict[str, Any]:
    out = dict(dados)
    out["finan_f_ref"] = f_curva
    out["sub_f_ref"] = s_curva
    fu = out.get("finan_usado")
    if fu is None or (isinstance(fu, (int, float)) and float(fu) == 0):
        out["finan_usado"] = float(f_curva or 0.0)
    su = out.get("fgts_sub_usado")
    if su is None or (isinstance(su, (int, float)) and float(su) == 0):
        out["fgts_sub_usado"] = float(s_curva or 0.0)
    return out


def build_fechamento_context(
    dados_cliente: Dict[str, Any],
    motor: MotorRecomendacao,
    premissas_dict: Dict[str, float] | None = None,
) -> Dict[str, Any]:
    """
    Retorna finan_f_ref, sub_f_ref, comparativo SAC/PRICE e taxa para os valores atuais
    (mesma lógica do bloco de `fechamento_aprovado` em app.py).
    """
    _prem = dict(DEFAULT_PREMISSAS)
    if premissas_dict:
        _prem.update(premissas_dict)

    f_curva, s_curva = atualizar_refs_curva(dados_cliente, motor)
    d = aplicar_defaults_fechamento(dict(dados_cliente), f_curva, s_curva)

    fin_u = float(d.get("finan_usado", 0) or 0)
    prazo = int(d.get("prazo_financiamento", 360) or 360)
    taxa = resolver_taxa_financiamento_anual_pct(d or {}, _prem)
    comp = calcular_comparativo_sac_price(fin_u, prazo, taxa)

    sac = comp["SAC"]
    price = comp["PRICE"]
    return {
        "finan_f_ref": f_curva,
        "sub_f_ref": s_curva,
        "dados_cliente": d,
        "taxa_financiamento_anual_pct": taxa,
        "comparativo": {
            "sac_primeira": sac["primeira"],
            "sac_ultima": sac["ultima"],
            "sac_juros": sac["juros"],
            "price_parcela": price["parcela"],
            "price_juros": price["juros"],
        },
    }


def arredondar_para_curva(
    valor_digitado: float,
    motor: MotorRecomendacao,
    renda: float,
    social: bool,
    cotista: bool,
    valor_avaliacao: float = 250000.0,
) -> Optional[float]:
    """Retorna o valor da curva de financiamento mais próximo do digitado."""
    df_f = motor.df_finan
    if df_f is None or df_f.empty:
        return None

    f_curva, _, faixa = motor.obter_enquadramento(renda, social, cotista, valor_avaliacao)

    s = "Sim" if social else "Nao"
    c = "Sim" if cotista else "Nao"
    col_fin = f"Finan_Social_{s}_Cotista_{c}_{faixa}"

    if col_fin not in df_f.columns:
        return None

    valores = pd.to_numeric(df_f[col_fin], errors="coerce").dropna()
    if valores.empty:
        return None

    unicos = valores.unique()
    idx = (pd.Series(unicos) - valor_digitado).abs().idxmin()
    arredondado = float(unicos[idx])
    logger.info("arredondar_para_curva: %.2f -> %.2f (col=%s)", valor_digitado, arredondado, col_fin)
    return arredondado
