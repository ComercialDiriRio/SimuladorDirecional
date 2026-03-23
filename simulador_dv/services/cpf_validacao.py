# -*- coding: utf-8 -*-
"""CPF — paridade com simulador_dv/app.py (sem pandas)."""
from __future__ import annotations

import re
from typing import Any


def limpar_cpf_visual(valor: Any) -> str:
    if valor is None or valor == "":
        return ""
    v_str = str(valor).strip()
    if v_str.endswith(".0"):
        v_str = v_str[:-2]
    v_nums = re.sub(r"\D", "", v_str)
    if v_nums:
        return v_nums.zfill(11)
    return ""


def formatar_cpf_saida(valor: Any) -> str:
    v = limpar_cpf_visual(valor)
    if len(v) == 11:
        return f"{v[:3]}.{v[3:6]}.{v[6:9]}-{v[9:]}"
    return v


def validar_cpf(cpf: Any) -> bool:
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


def aplicar_mascara_cpf(valor: Any) -> str:
    v = re.sub(r"\D", "", str(valor))[:11]
    if len(v) > 9:
        return f"{v[:3]}.{v[3:6]}.{v[6:9]}-{v[9:]}"
    if len(v) > 6:
        return f"{v[:3]}.{v[3:6]}.{v[6:]}"
    if len(v) > 3:
        return f"{v[:3]}.{v[3:]}"
    return v
