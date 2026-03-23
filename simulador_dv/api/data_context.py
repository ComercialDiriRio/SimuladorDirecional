# -*- coding: utf-8 -*-
"""Carrega DataFrames + motor (cache TTL alinhado a `load_sistema_dataframes`)."""
from __future__ import annotations

import time
from typing import Optional, Tuple

import pandas as pd

from simulador_dv.services.motor_recomendacao import MotorRecomendacao
from simulador_dv.services.sistema_data import load_sistema_dataframes, sistema_cache_ttl_sec

_ctx_bundle: Optional[
    Tuple[
        MotorRecomendacao,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        dict,
    ]
] = None
_ctx_when: float = 0.0


def clear_simulador_context_cache() -> None:
    global _ctx_bundle, _ctx_when
    _ctx_bundle = None
    _ctx_when = 0.0


def get_simulador_context() -> Tuple[
    MotorRecomendacao,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    dict,
]:
    """
    Retorna (motor, df_estoque, df_politicas, df_clientes, df_simulacoes, premissas_dict).
    Reutiliza a mesma instância de Motor enquanto o cache de sistema for válido.
    """
    global _ctx_bundle, _ctx_when
    now = time.monotonic()
    ttl = sistema_cache_ttl_sec()
    if _ctx_bundle is not None and (now - _ctx_when) < ttl:
        return _ctx_bundle

    df_finan, df_estoque, df_politicas, _df_logins, df_simulacoes, df_clientes, prem = load_sistema_dataframes()
    motor = MotorRecomendacao(df_finan, df_estoque, df_politicas)
    _ctx_bundle = (motor, df_estoque, df_politicas, df_clientes, df_simulacoes, prem)
    _ctx_when = now
    return _ctx_bundle
