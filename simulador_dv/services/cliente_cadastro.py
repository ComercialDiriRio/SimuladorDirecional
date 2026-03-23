# -*- coding: utf-8 -*-
"""Cadastro etapa `input` — mesma lógica do `form_cadastro` em app.py."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from simulador_dv.services.cpf_utils import aplicar_mascara_cpf, limpar_cpf_visual, validar_cpf
from simulador_dv.services.motor_recomendacao import MotorRecomendacao


def confirmar_cadastro(
    nome: str,
    cpf_val: str,
    data_nascimento: Optional[str],
    rendas_lista: List[float],
    qtd_participantes: int,
    ranking: str,
    politica_ps: str,
    social: bool,
    cotista: bool,
    motor: MotorRecomendacao,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Retorna (dados_cliente_delta, erro) — erro é mensagem ou None.
    """
    nome = (nome or "").strip()
    if not nome:
        return None, "Por favor, informe o Nome do Cliente."
    if not (cpf_val or "").strip():
        return None, "Por favor, informe o CPF do Cliente."
    cpf_formatado = aplicar_mascara_cpf(cpf_val)
    if not validar_cpf(cpf_val):
        return None, "CPF Inválido."

    renda_total_calc = sum(float(r or 0) for r in rendas_lista[: max(1, qtd_participantes)])
    if renda_total_calc <= 0:
        return None, "A renda total deve ser maior que zero."

    prazo_ps_max = 66 if politica_ps == "Emcash" else 84
    f_faixa_ref, s_faixa_ref, _ = motor.obter_enquadramento(renda_total_calc, social, cotista, valor_avaliacao=240000)

    delta: Dict[str, Any] = {
        "nome": nome,
        "cpf": limpar_cpf_visual(cpf_formatado),
        "data_nascimento": data_nascimento,
        "renda": renda_total_calc,
        "rendas_lista": [float(r) if r is not None else 0.0 for r in rendas_lista[:4]],
        "social": social,
        "cotista": cotista,
        "ranking": ranking,
        "politica": politica_ps,
        "qtd_participantes": qtd_participantes,
        "finan_usado_historico": 0.0,
        "ps_usado_historico": 0.0,
        "fgts_usado_historico": 0.0,
        "prazo_ps_max": prazo_ps_max,
        "limit_ps_renda": 0.30,
        "finan_f_ref": f_faixa_ref,
        "sub_f_ref": s_faixa_ref,
    }
    return delta, None
