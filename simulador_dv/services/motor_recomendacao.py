# -*- coding: utf-8 -*-
"""Motor de recomendação (espelho da lógica em app.py)."""
from __future__ import annotations

import pandas as pd


class MotorRecomendacao:
    def __init__(self, df_finan, df_estoque, df_politicas):
        self.df_finan = df_finan
        self.df_estoque = df_estoque
        self.df_politicas = df_politicas

    def obter_enquadramento(self, renda, social, cotista, valor_avaliacao=250000):
        if self.df_finan.empty:
            return 0.0, 0.0, "N/A"
        if valor_avaliacao <= 275000:
            faixa = "F2"
        elif valor_avaliacao <= 350000:
            faixa = "F3"
        else:
            faixa = "F4"
        renda_col = pd.to_numeric(self.df_finan["Renda"], errors="coerce").fillna(0)
        idx = (renda_col - float(renda)).abs().idxmin()
        row = self.df_finan.iloc[idx]
        s, c = ("Sim" if social else "Nao"), ("Sim" if cotista else "Nao")
        col_fin = f"Finan_Social_{s}_Cotista_{c}_{faixa}"
        col_sub = f"Subsidio_Social_{s}_Cotista_{c}_{faixa}"
        vf = row.get(col_fin, 0.0)
        vs = row.get(col_sub, 0.0)
        return float(vf), float(vs), faixa

    def calcular_poder_compra(self, renda, finan, fgts_sub, val_ps_limite):
        return (2 * renda) + finan + fgts_sub + val_ps_limite, val_ps_limite
