# -*- coding: utf-8 -*-
"""Utilitários de formatação extraídos de app.py (sem Streamlit)."""
from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd


def fmt_br(valor: Any) -> str:
    try:
        return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00"


def limpar_cpf_visual(valor: Any) -> str:
    if pd.isnull(valor) or valor == "":
        return ""
    v_str = str(valor).strip()
    if v_str.endswith(".0"):
        v_str = v_str[:-2]
    v_nums = re.sub(r"\D", "", v_str)
    if v_nums:
        return v_nums.zfill(11)
    return ""


def safe_float_convert(val: Any) -> float:
    if pd.isnull(val) or val == "":
        return 0.0
    if isinstance(val, (int, float, np.number)):
        return float(val)
    s = str(val).replace("R$", "").strip()
    try:
        return float(s)
    except Exception:
        if "," in s:
            s = s.replace(".", "").replace(",", ".")
        else:
            if s.count(".") >= 1:
                s = s.replace(".", "")
        try:
            return float(s)
        except Exception:
            return 0.0


def limpar_moeda(val: Any) -> float:
    return safe_float_convert(val)


def limpar_area_br(val: Any) -> float:
    """Converte área da planilha (ex.: 43,9 ou 51.53 m²) para float."""
    if val is None or val == "":
        return float("nan")
    if isinstance(val, (int, float, np.number)):
        if isinstance(val, float) and pd.isna(val):
            return float("nan")
        return float(val)
    s = str(val).strip().lower().replace("m²", "").replace("m2", "").strip()
    if not s or s == "nan":
        return float("nan")
    return float(safe_float_convert(s))
