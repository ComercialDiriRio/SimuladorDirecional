# -*- coding: utf-8 -*-
"""
Pro Soluto alinhado ao COMPARADOR TX EMCASH + SIMULADOR PS + POLITICAS.

Referências (excel_extracao_celulas.txt):
- I5: (PMT(E2, CF2, B41)*-1)*(1+E1)
- J8: B4 * (K3 - 30%) * (1 - E1)
- L8: PV(E2, K2, J8) * -1  (valor presente do fluxo de parcela máxima J8 em K2 meses)
- G15: min(int(L), POLITICAS col B * valor unidade)
- G14/C43: (K3 - 30%) * B4  (teto parcela simplificado, sem 1-E1)
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

import pandas as pd

from simulador_dv.config.taxas_comparador import OFFSET_LAMBDA, excel_e1, excel_e4_mensal
from simulador_dv.data.politicas_ps import PoliticaPSRow, resolve_politica_row
from simulador_dv.data.premissas import DEFAULT_PREMISSAS


def k3_lambda(renda: float, row: PoliticaPSRow) -> float:
    """K3 = IF(B4 < I1, I2, I3) com faixa e FX da linha POLITICAS."""
    r = float(renda or 0.0)
    if r < float(row.faixa_renda):
        return float(row.fx_renda_1)
    return float(row.fx_renda_2)


def fator_renda_liquido(k3: float) -> float:
    """(K3 - 30%) como no Excel (G14, núcleo da parcela sobre renda)."""
    return max(0.0, float(k3) - OFFSET_LAMBDA)


def parcela_max_g14(renda: float, k3: float) -> float:
    """SIMULADOR PS G14 / C43 linha simples: (K3-30%) * B4."""
    return float(renda or 0.0) * fator_renda_liquido(k3)


def parcela_max_j8(renda: float, k3: float, e1: float) -> float:
    """COMPARADOR J8: B4 * (K3-30%) * (1-E1)."""
    return float(renda or 0.0) * fator_renda_liquido(k3) * (1.0 - float(e1))


def pv_l8_positivo(e2_mensal: float, prazo_k2: int, parcela_j8: float) -> float:
    """
    L8 = -PV(E2, K2, J8) no Excel → valor positivo máximo de PS (PV de anuidade).
    """
    r = float(e2_mensal)
    n = int(prazo_k2 or 0)
    pmt = float(parcela_j8)
    if n <= 0 or pmt <= 0:
        return 0.0
    if abs(r) < 1e-15:
        return float(pmt * n)
    return float(pmt * (1.0 - (1.0 + r) ** (-n)) / r)


def cap_valor_unidade(valor_unidade: float, row: PoliticaPSRow) -> float:
    """POLITICAS col B × valor da unidade."""
    return float(valor_unidade or 0.0) * float(row.prosoluto_pct)


def valor_max_ps_g15(l_comparador: float, cap_politica_vu: float) -> float:
    """MIN(L, cap) — Excel usa int(L) no comparador; usamos floor para valores positivos."""
    lc = float(l_comparador)
    if lc > 0:
        lc = float(int(lc))
    cap = float(cap_politica_vu)
    return min(lc, cap) if lc > 0 else min(0.0, cap)


def parcela_ps_pmt(
    valor_ps: float,
    prazo_meses: int,
    premissas: Optional[Mapping[str, float]],
    politica_ui: str,
) -> float:
    """
    Parcela mensal do PS alinhada à célula **I5** do COMPARADOR TX EMCASH:
    `(PMT(E2, n, PV) × -1) × (1+E1)`.

    **E2** é **sempre** `emcash_fin_m` (**PREMISSAS B4**), igual ao **E2** global do comparador.
    A política de venda (Emcash/Direcional na UI) **não** altera esta taxa; ela só afeta
    tier/POLITICAS em `metricas_pro_soluto`. O financiamento do imóvel continua usando
    `taxa_mensal_financiamento_imobiliario` em outros módulos.

    `politica_ui` mantém compatibilidade de assinatura com a UI; é ignorado para E2.
    """
    _ = politica_ui  # API / Streamlit; I5 não troca E2 com Emcash vs Direcional
    p = dict(DEFAULT_PREMISSAS)
    if premissas:
        p.update({k: float(v) for k, v in premissas.items() if v is not None})
    e4 = excel_e4_mensal(p["ipca_aa"])
    e1 = excel_e1(p["tx_emcash_b5"], e4)
    pv = float(valor_ps or 0.0)
    n = int(prazo_meses or 0)
    if n <= 0 or pv <= 0:
        return 0.0
    e2 = float(p["emcash_fin_m"])
    if e2 <= -1:
        return 0.0
    try:
        # PMT Excel com PV>0 devolve valor negativo; I5 usa (PMT*-1)*(1+E1) → prestação positiva.
        pmt_excel = -pv * (e2 * (1 + e2) ** n) / ((1 + e2) ** n - 1)
        pmt_pos = abs(float(pmt_excel))
    except (ZeroDivisionError, ValueError, OverflowError):
        return 0.0
    return float(pmt_pos * (1.0 + e1))


def metricas_pro_soluto(
    renda: float,
    valor_unidade: float,
    politica_ui: str,
    ranking: str,
    premissas: Optional[Mapping[str, float]] = None,
    df_politicas: Optional[pd.DataFrame] = None,
    ps_cap_estoque: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Calcula tetos e valores de referência para exibição/validação na UI.

    E2 no PV (L8) usa sempre emcash_fin_m como no COMPARADOR (célula E2 global).
    """
    p = dict(DEFAULT_PREMISSAS)
    if premissas:
        p.update({k: float(v) for k, v in premissas.items() if v is not None})
    row = resolve_politica_row(politica_ui, ranking, df_politicas)
    e4 = excel_e4_mensal(p["ipca_aa"])
    e1 = excel_e1(p["tx_emcash_b5"], e4)
    k3 = k3_lambda(renda, row)
    j8 = parcela_max_j8(renda, k3, e1)
    g14 = parcela_max_g14(renda, k3)
    e2_comp = float(p["emcash_fin_m"])
    prazo_k2 = int(min(row.parcelas_max, 120.0))
    l8 = pv_l8_positivo(e2_comp, prazo_k2, j8)
    cap_vu = cap_valor_unidade(valor_unidade, row)
    ps_max_calc = valor_max_ps_g15(l8, cap_vu)
    if ps_cap_estoque is not None and float(ps_cap_estoque) > 0:
        ps_max_efetivo = min(ps_max_calc, float(ps_cap_estoque))
    else:
        ps_max_efetivo = ps_max_calc

    return {
        "politica_row": row,
        "k3": k3,
        "e1": e1,
        "parcela_max_j8": j8,
        "parcela_max_g14": g14,
        "pv_l8": l8,
        "cap_valor_unidade": cap_vu,
        "ps_max_comparador_politica": ps_max_calc,
        "ps_max_efetivo": ps_max_efetivo,
        "prazo_ps_politica": prazo_k2,
    }


def parcela_ps_para_valor(
    valor_ps: float,
    prazo_meses: int,
    politica_ui: str,
    premissas: Optional[Mapping[str, float]] = None,
) -> float:
    """Atalho para UI: parcela corrigida dado valor e prazo."""
    return parcela_ps_pmt(valor_ps, prazo_meses, premissas, politica_ui)
