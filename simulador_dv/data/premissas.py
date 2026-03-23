# -*- coding: utf-8 -*-
"""
Premissas alinhadas à aba PREMISSAS do Excel (SIMULADOR PS DIRE RIO V2).
B2/B3: taxas mensais pré/pós (Direcional, encadeamentos PV no Comparador).
B4: taxa mensal financiamento Emcash (célula E2 do Comparador TX Emcash).
B5, B6: componentes E1 = B5 + E4, E4 = (1+B6)^(1/12)-1 (IPCA a.a. em decimal).
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

# Valores extraídos de excel_extracao_celulas.txt (aba PREMISSAS)
DEFAULT_PREMISSAS: Dict[str, float] = {
    "dire_pre_m": 0.005,      # B2 a.m.
    "dire_pos_m": 0.015,      # B3 a.m.
    "emcash_fin_m": 0.0089,   # B4 a.m. → E2 no Comparador
    "tx_emcash_b5": 0.035,    # B5 (somado a E4 no Excel em E1)
    "ipca_aa": 0.05307,       # B6 a.a. (decimal)
    "renda_f2": 4700.0,
    "renda_f3": 8600.0,
    "renda_f4": 12000.0,
    "vv_f2": 275000.0,
    "vv_f3": 350000.0,
    "vv_f4": 500000.0,
    # Mantém paridade com o app antes da correção Emcash (financiamento Direcional)
    "direcional_fin_aa_pct": 8.16,
}

# Rótulos da coluna A do Excel → chaves internas
_LABEL_MAP = {
    "DIRE PRE": "dire_pre_m",
    "DIRE POS": "dire_pos_m",
    "EMCASH": "emcash_fin_m",
    "TX EMCASH": "tx_emcash_b5",
    "IPCA EMCASH": "ipca_aa",
    "RENDA F2": "renda_f2",
    "RENDA F3": "renda_f3",
    "RENDA F4": "renda_f4",
    "VV F2": "vv_f2",
    "VV F3": "vv_f3",
    "VV F4": "vv_f4",
}


def _to_float(x: Any) -> Optional[float]:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace("%", "").replace("R$", "")
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def premissas_from_dataframe(df: pd.DataFrame | None) -> Dict[str, float]:
    """Interpreta planilha estilo PREMISSAS (col A rótulo, col B valor) ou chave/valor."""
    out = dict(DEFAULT_PREMISSAS)
    if df is None or df.empty:
        return out
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    cols = list(df.columns)
    if len(cols) >= 2:
        c0, c1 = cols[0], cols[1]
        for _, row in df.iterrows():
            label = str(row.get(c0, "")).strip().upper()
            val = _to_float(row.get(c1))
            if val is None:
                continue
            for k_excel, key in _LABEL_MAP.items():
                if k_excel.upper() in label or label == k_excel.upper():
                    out[key] = val
                    break
    return out
