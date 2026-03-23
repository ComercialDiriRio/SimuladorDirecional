# -*- coding: utf-8 -*-
"""Funções financeiras espelho de app.py (SAC/PRICE, parcela financiamento)."""
from __future__ import annotations

from typing import Any, Dict


def calcular_comparativo_sac_price(valor, meses, taxa_anual) -> Dict[str, Any]:
    if valor is None or valor <= 0 or meses <= 0:
        return {"SAC": {"primeira": 0, "ultima": 0, "juros": 0}, "PRICE": {"parcela": 0, "juros": 0}}
    i = (1 + taxa_anual / 100) ** (1 / 12) - 1
    try:
        pmt_price = valor * (i * (1 + i) ** meses) / ((1 + i) ** meses - 1)
        total_pago_price = pmt_price * meses
        juros_price = total_pago_price - valor
    except Exception:
        pmt_price = 0
        juros_price = 0
    try:
        amort = valor / meses
        pmt_sac_ini = amort + (valor * i)
        pmt_sac_fim = amort + (amort * i)
        total_pago_sac = (pmt_sac_ini + pmt_sac_fim) * meses / 2
        juros_sac = total_pago_sac - valor
    except Exception:
        pmt_sac_ini = 0
        pmt_sac_fim = 0
        juros_sac = 0
    return {
        "SAC": {"primeira": pmt_sac_ini, "ultima": pmt_sac_fim, "juros": juros_sac},
        "PRICE": {"parcela": pmt_price, "juros": juros_price},
    }


def calcular_parcela_financiamento(valor_financiado, meses, taxa_anual_pct, sistema) -> float:
    if valor_financiado is None or valor_financiado <= 0 or meses <= 0:
        return 0.0
    i_mensal = (1 + taxa_anual_pct / 100) ** (1 / 12) - 1
    if sistema == "PRICE":
        try:
            return valor_financiado * (i_mensal * (1 + i_mensal) ** meses) / ((1 + i_mensal) ** meses - 1)
        except Exception:
            return 0.0
    amortizacao = valor_financiado / meses
    juros = valor_financiado * i_mensal
    return amortizacao + juros
