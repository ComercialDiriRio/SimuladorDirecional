# -*- coding: utf-8 -*-
"""
Constantes e funções de taxas alinhadas ao COMPARADOR TX EMCASH / PREMISSAS.

- E4 = (1 + IPCA a.a.)^(1/12) - 1
- E1 = B5 (TX EMCASH) + E4  → usado em (1+E1) na parcela do PS (célula I5).
- Offset 30% sobre λ (POLITICAS) antes da renda: (K3 - 30%) como no Excel.
"""
from __future__ import annotations

# Mesmo literal do Excel: subtrai 30% do parâmetro de política para obter % líquido de renda.
OFFSET_LAMBDA: float = 0.30


def excel_e4_mensal(ipca_aa: float) -> float:
    """E4 = (1+E3)^(1/12)-1 com E3 = IPCA anual em decimal."""
    return (1.0 + float(ipca_aa)) ** (1.0 / 12.0) - 1.0


def excel_e1(tx_emcash_b5: float, e4: float) -> float:
    """E1 = B5 + E4 (espelho literal do Excel)."""
    return float(tx_emcash_b5) + float(e4)
