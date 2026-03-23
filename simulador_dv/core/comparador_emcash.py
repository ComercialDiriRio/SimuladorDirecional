# -*- coding: utf-8 -*-
"""
Lógica em Python espelhando trechos da aba COMPARADOR TX EMCASH + PREMISSAS.

Referências principais (Excel):
- E2 = PREMISSAS!B4  (taxa mensal financiamento Emcash)
- E3 = PREMISSAS!B6, E4 = (1+E3)^(1/12)-1
- E1 = PREMISSAS!B5 + E4
- B3: IF(B41=0,0.99, B41 + B41*((1+0.5%)^4-1))  — valor PS ajustado no comparador
- PMT(E2, CF2, pv) no Excel usa taxa MENSAL E2 diretamente.

O app legado usa taxa anual em % e converte para mensal com (1+aa/100)^(1/12)-1.
Aqui normalizamos: calculamos taxa mensal efetiva do financiamento e convertemos
para % a.a. equivalente para alimentar calcular_parcela_financiamento / fluxo.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from simulador_dv.config.taxas_comparador import excel_e1, excel_e4_mensal
from simulador_dv.data.premissas import DEFAULT_PREMISSAS


def valor_ps_ajustado_comparador(ps_total: float) -> float:
    """
    COMPARADOR TX EMCASH!B3:
    IF(B41=0,0.99, B41 + B41*((1+0.5%)^4-1))
    """
    if ps_total is None or float(ps_total) == 0.0:
        return 0.99
    b41 = float(ps_total)
    return b41 + b41 * ((1.005) ** 4 - 1.0)


def _politica_emcash(politica: Any) -> bool:
    s = str(politica or "").strip().upper()
    return "EMCASH" in s


def taxa_mensal_financiamento_imobiliario(
    politica: Any,
    premissas: Optional[Mapping[str, float]] = None,
) -> float:
    """
    Taxa mensal usada no PMT / SAC / PRICE do **financiamento do imóvel**.
    - Emcash: mensal direta B4 (0.0089 no Excel de referência).
    - Direcional: derivada de direcional_fin_aa_pct (padrão 8.16% a.a.).
    """
    p = dict(DEFAULT_PREMISSAS)
    if premissas:
        p.update({k: float(v) for k, v in premissas.items() if v is not None})
    if _politica_emcash(politica):
        return float(p["emcash_fin_m"])
    aa = float(p.get("direcional_fin_aa_pct", 8.16))
    return (1.0 + aa / 100.0) ** (1.0 / 12.0) - 1.0


def taxa_anual_pct_equivalente(taxa_mensal: float) -> float:
    """Converte taxa mensal efetiva em % a.a. equivalente (composta)."""
    return ((1.0 + float(taxa_mensal)) ** 12 - 1.0) * 100.0


def resolver_taxa_financiamento_anual_pct(
    dados_cliente: Mapping[str, Any],
    premissas: Optional[Mapping[str, float]] = None,
) -> float:
    """
    Taxa anual em % compatível com calcular_parcela_financiamento /
    calcular_fluxo_pagamento_detalhado / calcular_comparativo_sac_price.
    """
    i_m = taxa_mensal_financiamento_imobiliario(
        dados_cliente.get("politica", ""),
        premissas,
    )
    return taxa_anual_pct_equivalente(i_m)


def parcela_ps_emcash_pmt(
    valor_ps: float,
    prazo_meses: int,
    premissas: Optional[Mapping[str, float]] = None,
) -> float:
    """
    Espelha COMPARADOR!I5: (PMT(E2, CF2, B41)*-1)*(1+E1)
    Delega a pro_soluto_comparador.parcela_ps_pmt (Emcash).
    """
    from simulador_dv.core.pro_soluto_comparador import parcela_ps_pmt

    return parcela_ps_pmt(valor_ps, prazo_meses, premissas, "Emcash")


def metricas_comparador_tx(
    dados_cliente: Mapping[str, Any],
    premissas: Optional[Mapping[str, float]] = None,
) -> Dict[str, float]:
    """Resumo para debug / UI: taxas e ajustes usados no ramo Emcash."""
    p = dict(DEFAULT_PREMISSAS)
    if premissas:
        p.update({k: float(v) for k, v in premissas.items() if v is not None})
    e4 = excel_e4_mensal(p["ipca_aa"])
    e1 = excel_e1(p["tx_emcash_b5"], e4)
    i_m = taxa_mensal_financiamento_imobiliario(
        dados_cliente.get("politica", ""), p
    )
    return {
        "taxa_mensal_fin_imv": i_m,
        "taxa_anual_fin_imv_pct": taxa_anual_pct_equivalente(i_m),
        "e1_comparador": e1,
        "e4_ipca_mensal": e4,
        "emcash_fin_mensal": float(p["emcash_fin_m"]),
    }
