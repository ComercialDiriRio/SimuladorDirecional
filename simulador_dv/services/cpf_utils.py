# -*- coding: utf-8 -*-
"""CPF — espelho de app.py (sem Streamlit)."""
from __future__ import annotations

import re

from simulador_dv.services.format_utils import limpar_cpf_visual


def aplicar_mascara_cpf(valor) -> str:
    v = re.sub(r"\D", "", str(valor))
    v = v[:11]
    if len(v) > 9:
        return f"{v[:3]}.{v[3:6]}.{v[6:9]}-{v[9:]}"
    if len(v) > 6:
        return f"{v[:3]}.{v[3:6]}.{v[6:]}"
    if len(v) > 3:
        return f"{v[:3]}.{v[3:]}"
    return v


def validar_cpf(cpf: str) -> bool:
    cpf = re.sub(r"\D", "", str(cpf))
    if len(cpf) != 11 or len(set(cpf)) == 1:
        return False
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0
    if resto != int(cpf[9]):
        return False
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0
    if resto != int(cpf[10]):
        return False
    return True
