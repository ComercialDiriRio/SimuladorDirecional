# -*- coding: utf-8 -*-
"""
=============================================================================
SISTEMA DE SIMULAÇÃO IMOBILIÁRIA - DIRE RIO V69 (SINGLE SOURCE - UPDATE)
=============================================================================
Alinhado com o app Flask (SimuladorDV): mesmo catálogo (JSON), normalização
de estoque (Empreendimento, PS_Diamante/PS_Ouro/.../PS_Aco), viabilidade
(2*renda + finan + sub + PS_rank) e recomendações IDEAL/SEGURO/FACILITADO.
"""

import streamlit as st
import pandas as pd
import numpy as np
import re
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components
import base64
from datetime import datetime, date
import time
import locale
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
import json
import pytz
import altair as alt
import folium
from streamlit_folium import st_folium
import math
import json
import urllib.parse

from simulador_dv.config.constants import (
    ID_GERAL,
    URL_FINAN,
    URL_RANKING,
    URL_ESTOQUE,
    URL_FAVICON_RESERVA,
    URL_LOGO_DIRECIONAL_BIG,
    COR_AZUL_ESC,
    COR_VERMELHO,
    COR_FUNDO,
    COR_BORDA,
    COR_TEXTO_MUTED,
    COR_INPUT_BG,
)
from simulador_dv.data.premissas import DEFAULT_PREMISSAS, premissas_from_dataframe
from simulador_dv.core.comparador_emcash import resolver_taxa_financiamento_anual_pct
from simulador_dv.core.pro_soluto_comparador import metricas_pro_soluto, parcela_ps_para_valor
from simulador_dv.ui.inject import inject_gallery_modal, inject_streamlit_styles, scroll_to_top_component
from simulador_dv.services.motor_recomendacao import MotorRecomendacao
from simulador_dv.services.pagamento_fluxo import calcular_fluxo_pagamento_detalhado
from simulador_dv.services.pdf_resumo import gerar_resumo_pdf
from simulador_dv.services.email_smtp import enviar_email_smtp

# Tenta importar fpdf e PIL
try:
    from fpdf import FPDF
    PDF_ENABLED = True
except ImportError:
    PDF_ENABLED = False

try:
    from PIL import Image
except ImportError:
    Image = None

# Configuração de Locale
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR')
    except:
        pass

# =============================================================================
# 0. CATÁLOGO E UTILITÁRIOS (constantes em simulador_dv.config.constants)
# =============================================================================
# --- CATALOGO DE PRODUTOS COMPLETO ---
CATALOGO_PRODUTOS = {
    "CONQUISTA FLORIANÓPOLIS": {
        "video": "https://www.youtube.com/watch?v=oU5SeVbmCsk",
        "lat": -22.8878, "lon": -43.3567,
        "imagens": [
            {"nome": "Fachada", "link": "https://drive.google.com/file/d/1FtNq9m06iZ3ZAce1Eu8GXYeaUDhBSiV8/view?usp=drivesdk"},
            {"nome": "Piscina Adulto", "link": "https://drive.google.com/file/d/1ud4Vk3oD2Gmcc9eOEMW-rn-2mIr1zGON/view?usp=drivesdk"},
            {"nome": "Playground", "link": "https://drive.google.com/file/d/187TeBEzv2qbJQfbU8m30g7BDbs5kPYx8/view?usp=drivesdk"},
            {"nome": "Salão de Festas", "link": "https://drive.google.com/file/d/1dTFFbyexiIJCk1k4-catyJ_dynvPj7Vj/view?usp=drivesdk"},
            {"nome": "Fitness Externo", "link": "https://drive.google.com/file/d/1pY9CikHmAqYwxBYj5ohLmqNC0S_fzXKu/view?usp=drivesdk"},
            {"nome": "Guarita", "link": "https://drive.google.com/file/d/1lMWl5-1OpjYKDLmX38Du9OQeYmUT-CwC/view?usp=drivesdk"},
            {"nome": "Apartamento Garden", "link": "https://drive.google.com/file/d/1u2pc7a6P4DOPYp69RN0icmOZoTFriuKt/view?usp=drivesdk"},
            {"nome": "Planta Tipo Meio", "link": "https://drive.google.com/file/d/1b4QxziB56rrcxMpgVMMNHN0XnPoKelFP/view?usp=drivesdk"},
            {"nome": "Planta Garden", "link": "https://drive.google.com/file/d/13fzvOhPY8uVlBhmbhCQrAnEbse4wv7MY/view?usp=drivesdk"},
            {"nome": "Masterplan", "link": "https://drive.google.com/file/d/1fR7GFbh9a-J3o3hv21bBbxudiW5-I6pe/view?usp=drivesdk"},
            {"nome": "Ficha Técnica", "link": "https://drive.google.com/file/d/1u5KoeItcTYVgAfkk5UjqrI83lSjt0i2u/view?usp=drivesdk"}
        ]
    },
    "ITANHANGÁ GREEN": {
        "video": "https://www.youtube.com/watch?v=Lt74juwBMXM",
        "lat": -22.9733, "lon": -43.3364,
        "imagens": [
            {"nome": "Fachada", "link": "https://drive.google.com/file/d/1PvfgCc1O6NfPsNpGxjzChduroYoCQGsF/view?usp=drivesdk"},
            {"nome": "Piscina", "link": "https://drive.google.com/file/d/1tB0lFoYSDuL8pVj8_eArd8edYJ7a-Zd-/view?usp=drivesdk"},
            {"nome": "Playground", "link": "https://drive.google.com/file/d/1_WWAQE_286TpbaNizsQVwCjMamahuOft/view?usp=drivesdk"},
            {"nome": "Salão de Festas", "link": "https://drive.google.com/file/d/124HX2LthZRYI_FeMvZ9T-6WBVK-M94TT/view?usp=drivesdk"},
            {"nome": "Guarita", "link": "https://drive.google.com/file/d/1C6mF2DS_X1QCYkhfYzCSmd0Ror_S4m3x/view?usp=drivesdk"},
            {"nome": "Planta Tipo", "link": "https://drive.google.com/file/d/1_v9Vy03-j5U9lppXubsWtAib4DEAiUCz/view?usp=drivesdk"},
            {"nome": "Planta Garden", "link": "https://drive.google.com/file/d/1etHATpKkP0ctj7H3uhFXHrAfB7xqpai3/view?usp=drivesdk"},
            {"nome": "Masterplan", "link": "https://drive.google.com/file/d/1NXXcLhPiiZiquei9QH8_QM1M19tpXVp8/view?usp=drivesdk"},
            {"nome": "Ficha Técnica", "link": "https://drive.google.com/file/d/18OdrnhrmHmvv2mu_MskLflGCMBgJQC2r/view?usp=drivesdk"}
        ]
    },
    "MAX NORTE": {
        "video": "https://www.youtube.com/watch?v=cnzn1cpJ4tA",
        "lat": -22.8086, "lon": -43.3633,
        "imagens": [
            {"nome": "Fachada", "link": "https://drive.google.com/file/d/1AVdsT4MXMcH81K_EFUS2kgSU9luS6oCg/view?usp=drivesdk"},
            {"nome": "Piscina", "link": "https://drive.google.com/file/d/1SECUIdrQC62v1Q4J7Rgwlh257PGcfyIB/view?usp=drivesdk"},
            {"nome": "Playground", "link": "https://drive.google.com/file/d/1d_33bONdid1qZgwTMieCUQsQ_QX0e5H6/view?usp=drivesdk"},
            {"nome": "Salão Gourmet", "link": "https://drive.google.com/file/d/1U_J6KqdChx3dTFwdPSm-EQHyrKUk4nbe/view?usp=drivesdk"},
            {"nome": "Guarita", "link": "https://drive.google.com/file/d/1KFpxyD0eTgXAJ_Te6b0Jl41s8d0S0Dmk/view?usp=drivesdk"},
            {"nome": "Apartamento", "link": "https://drive.google.com/file/d/1BQXjmuE_EU1WtPpoqhRsQzrHdBKkuY9a/view?usp=drivesdk"},
            {"nome": "Planta Tipo", "link": "https://drive.google.com/file/d/1a9f7v6YFbpOhczb7nG_JeGtcgsXi0Fv7/view?usp=drivesdk"},
            {"nome": "Masterplan", "link": "https://drive.google.com/file/d/1s4WwrmqiPxBTq3McM6dae4mauGw3PpI5/view?usp=drivesdk"}
        ]
    },
    "NORTE CLUBE": {
        "video": "https://www.youtube.com/watch?v=ElO6Q95Hsak",
        "lat": -22.8752, "lon": -43.2905,
        "imagens": [
            {"nome": "Fachada", "link": "https://drive.google.com/file/d/1CdMMB44Em88E4dmaNyq-YJe4eEX53NEE/view?usp=drivesdk"},
            {"nome": "Piscina", "link": "https://drive.google.com/file/d/1khrmZKSMV5uhh68tvdE10iM28yxvGBMK/view?usp=drivesdk"},
            {"nome": "Playground", "link": "https://drive.google.com/file/d/1EKaLDk6GTJcIbY7VNVXnnurGqxTmhdxi/view?usp=drivesdk"},
            {"nome": "Salão de Festas", "link": "https://drive.google.com/file/d/1IpwQYtIKde8EoOoDPGVGwoRmQ73b0ht8/view?usp=drivesdk"},
            {"nome": "Quadra", "link": "https://drive.google.com/file/d/1j-n1kjGXcOzc2cUDl8yYA7drkXNZBrZK/view?usp=drivesdk"},
            {"nome": "Planta Tipo", "link": "https://drive.google.com/file/d/1AQc25GcW2-YCBNUIlcRMBVnjFAL1oSuQ/view?usp=drivesdk"},
            {"nome": "Planta Garden", "link": "https://drive.google.com/file/d/1ZL0l-x6ZnLLTFx_DZw7IIi3YeLkumlw3/view?usp=drivesdk"},
            {"nome": "Ficha Técnica", "link": "https://drive.google.com/file/d/1DMmjq6Mu785xMfuUq0DFcAnLV1LpnW4Z/view?usp=drivesdk"}
        ]
    },
    "CONQUISTA OCEÂNICA": {
        "video": "https://www.youtube.com/watch?v=4g5oy3SCh-A",
        "lat": -22.8711, "lon": -43.0133,
        "imagens": [
            {"nome": "Fachada", "link": "https://drive.google.com/file/d/1hIsxtMe-5NyiIIy7nXxFNcndCamuX1pu/view?usp=drivesdk"},
            {"nome": "Piscina", "link": "https://drive.google.com/file/d/1Q488b06oCll4iwU5l_BgVJEEn4uVneho/view?usp=drivesdk"},
            {"nome": "Playground", "link": "https://drive.google.com/file/d/1zQyrd4ZYb45bw76z7cajjZkiHjJnubbY/view?usp=drivesdk"},
            {"nome": "Salão de Festas", "link": "https://drive.google.com/file/d/147z9BlYfjqEMc1yvHuosVHLEKATBSvjd/view?usp=drivesdk"},
            {"nome": "Guarita", "link": "https://drive.google.com/file/d/1O6COShsXlNGtzeewOBRnUE45NVNIiOoh/view?usp=drivesdk"},
            {"nome": "Planta Tipo", "link": "https://drive.google.com/file/d/14RsOJBM6jYDF4KumRCz1sCzj3Aix-UjT/view?usp=drivesdk"},
            {"nome": "Planta Garden", "link": "https://drive.google.com/file/d/1BdldmlPt_97aAfcl_7YMp5uy7WJgs10U/view?usp=drivesdk"},
            {"nome": "Ficha Técnica", "link": "https://drive.google.com/file/d/1vD4q4gkD31Nm4qL4pHs3zLytUq3MFfii/view?usp=drivesdk"}
        ]
    },
    "PARQUE IGUAÇU": {
        "video": "https://www.youtube.com/watch?v=PQOA5AS0Sdo",
        "lat": -22.7758, "lon": -43.4861,
        "imagens": [
            {"nome": "Fachada", "link": "https://drive.google.com/file/d/1mdp1DBxGd7WpG-1BB67BDLHlJ_EAtj0V/view?usp=drivesdk"},
            {"nome": "Piscina", "link": "https://drive.google.com/file/d/1TTTiFl605kS0LiztlzXfvn1hRj_X4_Fc/view?usp=drivesdk"},
            {"nome": "Playground", "link": "https://drive.google.com/file/d/1jqjS025JccXTkMOP2QXBKAAc-4vKF5SN/view?usp=drivesdk"},
            {"nome": "Salão de Festas", "link": "https://drive.google.com/file/d/1UJlpQm5rJqaZrF5DGgTmW8ygNLWpsp2y/view?usp=drivesdk"},
            {"nome": "Churrasqueira", "link": "https://drive.google.com/file/d/1d1vxr_-Nb5A7iyLc_Mn7FqCwBUxwO3oZ/view?usp=drivesdk"},
            {"nome": "Planta Tipo", "link": "https://drive.google.com/file/d/1FiSP0QP2EBRRWlYGsgd4ZkyLiqEWn5CG/view?usp=drivesdk"},
            {"nome": "Planta Garden", "link": "https://drive.google.com/file/d/1uVoJkhPvylOMFRcJlR1bsfvBUAVwVVlv/view?usp=drivesdk"},
            {"nome": "Ficha Técnica", "link": "https://drive.google.com/file/d/1m529O3c6pEz3sD3-Vba1BAUJKzj9XOxg/view?usp=drivesdk"}
        ]
    },
    "SOUL SAMBA": {
        "video": "https://www.youtube.com/watch?v=qTPaarVhHgs",
        "lat": -22.8778, "lon": -43.2778,
        "imagens": [
            {"nome": "Fachada", "link": "https://drive.google.com/file/d/1Iv-887JKrY-h6wSktD_SXjeLZM28n4-Y/view?usp=drivesdk"},
            {"nome": "Piscina", "link": "https://drive.google.com/file/d/14JNb9eQJLCbBkaIEExDmf9dH6yP3vKKA/view?usp=drivesdk"},
            {"nome": "Playground", "link": "https://drive.google.com/file/d/16FjIZzAVVXouhm8eEwjDbArC8XsX2552/view?usp=drivesdk"},
            {"nome": "Salão de Festas", "link": "https://drive.google.com/file/d/1wJszyTa-w1N6pczz2UJx6xi5zlDMhSeU/view?usp=drivesdk"},
            {"nome": "Guarita", "link": "https://drive.google.com/file/d/1MqZBsikoiaDY-TD2Wm759WJV8Ozy-Li7/view?usp=drivesdk"},
            {"nome": "Planta Tipo", "link": "https://drive.google.com/file/d/14RtGmEXYyFNkI33WMRD_NFD2M3OdOwj7/view?usp=drivesdk"},
            {"nome": "Ficha Técnica", "link": "https://drive.google.com/file/d/1-hI2guSTSTHiynWe3QpC-CcXeuf2IhTs/view?usp=drivesdk"}
        ]
    },
    "VERT ALCÂNTARA": {
        "video": "https://www.youtube.com/watch?v=Lag2kS7wFnU",
        "lat": -22.8222, "lon": -43.0031,
        "imagens": [
            {"nome": "Fachada", "link": "https://drive.google.com/file/d/1Hk_xywnFmA68J0lcuM6h9qK3GKgFT7Yt/view?usp=drivesdk"},
            {"nome": "Piscina", "link": "https://drive.google.com/file/d/1pDm2u3z3pKqqqzMkYb93LIceScYzDFs_/view?usp=drivesdk"},
            {"nome": "Coworking", "link": "https://drive.google.com/file/d/1XiffjmMTws-9ciqEhh6FiRI3MYSSROnh/view?usp=drivesdk"},
            {"nome": "Sala de Jogos", "link": "https://drive.google.com/file/d/1hdENx08aVZBQP-df_l2fZOQ4FQF984DL/view?usp=drivesdk"},
            {"nome": "Planta Tipo", "link": "https://drive.google.com/file/d/1D_zDCDaQVvK4DBc9UtURZSptGKZsvgb8/view?usp=drivesdk"},
            {"nome": "Planta Garden", "link": "https://drive.google.com/file/d/1C2x7nZoKAJ7DNqsqxIai4wFOW032sTqi/view?usp=drivesdk"}
        ]
    },
    "INN BARRA OLÍMPICA": {
        "video": "https://www.youtube.com/watch?v=SGEJFc3jh5A",
        "lat": -22.9567, "lon": -43.3761,
        "imagens": [
            {"nome": "Fachada", "link": "https://drive.google.com/file/d/1ScG09d2xcPblZKQJYlssw-AMSOLmx6qO/view?usp=drivesdk"},
            {"nome": "Piscina", "link": "https://drive.google.com/file/d/1cYMq0jujtHC_DPUXrNpRf4jYN_83ntiK/view?usp=drivesdk"},
            {"nome": "Playground", "link": "https://drive.google.com/file/d/1gaORQ2t3vur097TWHrGL_fF3oqSt6REu/view?usp=drivesdk"},
            {"nome": "Salão de Festas", "link": "https://drive.google.com/file/d/1jYIt95E4_k0HhCpTCn7lBEM91G_VJLTF/view?usp=drivesdk"},
            {"nome": "Planta Tipo", "link": "https://drive.google.com/file/d/1t-ZAfSHeyYWUgJx-2q00LpU15QSjSinh/view?usp=drivesdk"},
            {"nome": "Ficha Técnica", "link": "https://drive.google.com/file/d/1CEykILUVyBfz0o73QFdjyIbvpof5P28w/view?usp=drivesdk"}
        ]
    },
    "NOVA CAXIAS FUN": {
        "video": "https://www.youtube.com/watch?v=3P_o4jVWsOI",
        "lat": -22.7303, "lon": -43.3075,
        "imagens": [
            {"nome": "Fachada", "link": "https://drive.google.com/file/d/17YwXWQPvTXWX0bx0sNq9lX8ZN6r3Q7_F/view?usp=drivesdk"},
            {"nome": "Piscina", "link": "https://drive.google.com/file/d/1jB16KnKTOdxFpj68OqOnnzlPl1ev1gyW/view?usp=drivesdk"},
            {"nome": "Playground", "link": "https://drive.google.com/file/d/1-OM3XVNlYgfo2az26feqDfoYCjUxn7-d/view?usp=drivesdk"},
            {"nome": "Salão de Festas", "link": "https://drive.google.com/file/d/1DBoZI2zVeycc3KnmKAhwFIK1GkMefb_X/view?usp=drivesdk"},
            {"nome": "Planta Tipo", "link": "https://drive.google.com/file/d/1Te0683dB6MeOr_5JbXpEkhkb-Qcu_iBJ/view?usp=drivesdk"},
            {"nome": "Ficha Técnica", "link": "https://drive.google.com/file/d/14l-h7mPypMoAFq7inaT-azt1CaP_evqF/view?usp=drivesdk"}
        ]
    },
    "NOVA CAXIAS UP": {
        "video": "https://www.youtube.com/watch?v=EbEcZvIdTvY",
        "lat": -22.7303, "lon": -43.3075,
        "imagens": [
            {"nome": "Fachada", "link": "https://drive.google.com/file/d/12I_GnSQVtCp-rdnUu3mUh43fc4qG54Ke/view?usp=drivesdk"},
            {"nome": "Piscina", "link": "https://drive.google.com/file/d/1cGDJJN79thO85xEyz74TvqIh6h4vsuCl/view?usp=drivesdk"},
            {"nome": "Playground", "link": "https://drive.google.com/file/d/13qIgtrn55FD46nNMOYrr04r9JRvbTpZ0/view?usp=drivesdk"},
            {"nome": "Salão de Festas", "link": "https://drive.google.com/file/d/1_lJXmBx02NVA9pjWkR9DGDM6JQbQOkU8/view?usp=drivesdk"},
            {"nome": "Planta Tipo", "link": "https://drive.google.com/file/d/1FimZCNjC9Jy4ByW5n2-FOukEqoFGER87/view?usp=drivesdk"},
            {"nome": "Ficha Técnica", "link": "https://drive.google.com/file/d/1gvehESpzNk4rqhA-bUOW_9YOT8XpEsi1/view?usp=drivesdk"}
        ]
    },
    "RESERVA DO SOL": {
        "video": "https://www.youtube.com/watch?v=Wij9XjG4slM",
        "lat": -22.9536, "lon": -43.3858,
        "imagens": [
            {"nome": "Fachada", "link": "https://drive.google.com/file/d/1-RFBc4sQ7Tbo6qwhP3GXZQy3m7_DtFcB/view?usp=drivesdk"},
            {"nome": "Piscina", "link": "https://drive.google.com/file/d/1HUqoUz1--CdmuZYd0DIvPhlyk9MnDt_O/view?usp=drivesdk"},
            {"nome": "Playground", "link": "https://drive.google.com/file/d/1BnEkT8v6OCRdhx624sJRMPfcMjJsU2Tb/view?usp=drivesdk"},
            {"nome": "Salão de Festas", "link": "https://drive.google.com/file/d/13xuG8_MJF_yM0Mt9Nnzft10mdGE4KbFn/view?usp=drivesdk"},
            {"nome": "Planta Meio", "link": "https://drive.google.com/file/d/11wX-XPBMHOAqpKZUuwwJpJ_GcsiRxU1c/view?usp=drivesdk"},
            {"nome": "Ficha Técnica", "link": "https://drive.google.com/file/d/1Cj-EuPHMF86pe7s0nw6XML2esCTd4Nqn/view?usp=drivesdk"}
        ]
    },
    "RESIDENCIAL JERIVÁ": {
        "video": "https://www.youtube.com/watch?v=GdEvqLVXeFw",
        "lat": -22.8944, "lon": -43.5575,
        "imagens": [
            {"nome": "Fachada", "link": "https://drive.google.com/file/d/1nzOHc7-n7gZDAFSbdNwDXgnQAJNouRPU/view?usp=drivesdk"},
            {"nome": "Piscina", "link": "https://drive.google.com/file/d/1R-TYH7oauG_qSFGTZbFzHjSaPkRcCEHC/view?usp=drivesdk"},
            {"nome": "Playground", "link": "https://drive.google.com/file/d/1m4AHz4E5id5O5r5bI1-5zckXK5pPZ43s/view?usp=drivesdk"},
            {"nome": "Salão de Festas", "link": "https://drive.google.com/file/d/12HxPpDvQeYhamousSPF976-7hb2WDbFc/view?usp=drivesdk"},
            {"nome": "Planta Tipo", "link": "https://drive.google.com/file/d/1RnmcwKnMxy7jL5AbPUPFJToWV_O1PJV-/view?usp=drivesdk"},
            {"nome": "Ficha Técnica", "link": "https://drive.google.com/file/d/1i8X-05E1NWAOxAgSQ6K1aX70NDXUlIUN/view?usp=drivesdk"}
        ]
    },
    "RESIDENCIAL LARANJEIRAS": {
        "video": "https://www.youtube.com/watch?v=jmV1RHkRlZ4",
        "lat": -22.8944, "lon": -43.5575,
        "imagens": [
            {"nome": "Fachada", "link": "https://drive.google.com/file/d/19Eq2qFk5fx8AnG-ooWq6SsGGmQKsIvvb/view?usp=drivesdk"},
            {"nome": "Piscina", "link": "https://drive.google.com/file/d/1v9zn2HdtjNWBKlrxAKFljUkCD7SHSupB/view?usp=drivesdk"},
            {"nome": "Playground", "link": "https://drive.google.com/file/d/1xVLehaJSdy1xvz6eELz3I8VtSPoQ8C-c/view?usp=drivesdk"},
            {"nome": "Salão de Festas", "link": "https://drive.google.com/file/d/1WItdv2DY59gu-yzW1RXPykdCU5i2mdb2/view?usp=drivesdk"},
            {"nome": "Planta Tipo", "link": "https://drive.google.com/file/d/1noEQfz_FQ7w3s7oopg8FQwhvfUfccjuT/view?usp=drivesdk"}
        ]
    },
    "VIVA VIDA REALENGO": {
        "video": "https://www.youtube.com/watch?v=cfRvstasGaw",
        "lat": -22.8797, "lon": -43.4286,
        "imagens": [
            {"nome": "Fachada", "link": "https://drive.google.com/file/d/1plxTT4MmRUP4xUl_300Rz7eFSH36uLFw/view?usp=drivesdk"},
            {"nome": "Piscina", "link": "https://drive.google.com/file/d/1PT-z4PFD_VUTtxrPKoXJJ-lOL9ud17FQ/view?usp=drivesdk"},
            {"nome": "Playground", "link": "https://drive.google.com/file/d/1j51NJUlnu7M4T1Bwax7UfmorEhv5dYu4/view?usp=drivesdk"},
            {"nome": "Planta Tipo", "link": "https://drive.google.com/file/d/17xl-SYLLtpyIxb82qkQAKHX1c4peLLcq/view?usp=drivesdk"},
            {"nome": "Ficha Técnica", "link": "https://drive.google.com/file/d/1-UfmBvETRRuvuq5R6rKA3Y_9s4xBzTc6/view?usp=drivesdk"}
        ]
    },
    "RECANTO CLUBE": {
        "video": "https://www.youtube.com/watch?v=7K3UUEIOT-8",
        "lat": -22.9694, "lon": -43.5936,
        "imagens": [
            {"nome": "Fachada", "link": "https://drive.google.com/file/d/1pfvsC4S15n4HbtWeNp2crJcs0PcH5MRV/view?usp=drivesdk"},
            {"nome": "Piscina", "link": "https://drive.google.com/file/d/19SDMm-pzyxBfK_jTK4Z5gp2-aLlW_Lxj/view?usp=drivesdk"},
            {"nome": "Playground", "link": "https://drive.google.com/file/d/1aOW9ErNYvbdmVPeyCKYdWH1Z32joTliw/view?usp=drivesdk"},
            {"nome": "Salão de Festas", "link": "https://drive.google.com/file/d/1bI4pk6j63uWBMmQnz07cDTNrB3YFCrpS/view?usp=drivesdk"},
            {"nome": "Planta Tipo", "link": "https://drive.google.com/file/d/1fOM-Ul_JZwjELDMkmwkHE_JN669V9-ob/view?usp=drivesdk"},
            {"nome": "Ficha Técnica", "link": "https://drive.google.com/file/d/1FT0IYF1VBWUX2iSxGqK7VuK-Z7sszSUK/view?usp=drivesdk"}
        ]
    }
}

def _load_catalogo_galeria():
    """Carrega catálogo de produtos (vídeos, mapa, imagens Drive) de JSON se existir (fonte única com app Flask)."""
    _here = os.path.dirname(os.path.abspath(__file__))
    _base = os.path.dirname(_here)  # raiz do projeto (pai de simulador_dv/)
    for path in [
        os.path.join(_base, "static", "img", "galeria", "catalogo_produtos.json"),
        os.path.join(_base, "catalogo_produtos.json"),
        os.path.join(_here, "static", "img", "galeria", "catalogo_produtos.json"),
    ]:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {}

# Se existir JSON do catálogo, usa como fonte (sobrescreve); senão mantém CATALOGO_PRODUTOS in-code
_catalogo_json = _load_catalogo_galeria()
if _catalogo_json:
    CATALOGO_PRODUTOS.update(_catalogo_json)

def fmt_br(valor):
    try:
        return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "0,00"

def limpar_cpf_visual(valor):
    if pd.isnull(valor) or valor == "": return ""
    v_str = str(valor).strip()
    # Remove decimal se existir
    if v_str.endswith('.0'): v_str = v_str[:-2]
    v_nums = re.sub(r'\D', '', v_str)
    # Garante 11 digitos preenchendo zeros a esquerda
    if v_nums: return v_nums.zfill(11)
    return ""

def formatar_cpf_saida(valor):
    v = limpar_cpf_visual(valor)
    if len(v) == 11:
        return f"{v[:3]}.{v[3:6]}.{v[6:9]}-{v[9:]}"
    return v

def validar_cpf(cpf):
    cpf = re.sub(r'\D', '', str(cpf))
    if len(cpf) != 11 or len(set(cpf)) == 1: return False
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    if resto == 10: resto = 0
    if resto != int(cpf[9]): return False
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    if resto == 10: resto = 0
    if resto != int(cpf[10]): return False
    return True

# Função para máscara automática de CPF
def aplicar_mascara_cpf(valor):
    # Remove tudo que não é dígito
    v = re.sub(r'\D', '', str(valor))
    # Limita a 11 dígitos
    v = v[:11]
    # Aplica máscara progressiva
    if len(v) > 9:
        return f"{v[:3]}.{v[3:6]}.{v[6:9]}-{v[9:]}"
    elif len(v) > 6:
        return f"{v[:3]}.{v[3:6]}.{v[6:]}"
    elif len(v) > 3:
        return f"{v[:3]}.{v[3:]}"
    return v

def safe_float_convert(val):
    if pd.isnull(val) or val == "": return 0.0
    if isinstance(val, (int, float, np.number)): return float(val)
    s = str(val).replace('R$', '').strip()
    try:
        return float(s)
    except:
        if ',' in s:
            s = s.replace('.', '').replace(',', '.')
        else:
            if s.count('.') >= 1:
                s = s.replace('.', '')
        try: return float(s)
        except: return 0.0

def calcular_cor_gradiente(valor):
    valor = max(0, min(100, valor))
    f = valor / 100.0
    r = int(227 + (0 - 227) * f)
    g = int(6 + (44 - 6) * f)
    b = int(19 + (93 - 19) * f)
    return f"rgb({r},{g},{b})"

def calcular_comparativo_sac_price(valor, meses, taxa_anual):
    if valor is None or valor <= 0 or meses <= 0:
        return {"SAC": {"primeira": 0, "ultima": 0, "juros": 0}, "PRICE": {"parcela": 0, "juros": 0}}
    i = (1 + taxa_anual/100)**(1/12) - 1
    
    # PRICE
    try:
        pmt_price = valor * (i * (1 + i)**meses) / ((1 + i)**meses - 1)
        total_pago_price = pmt_price * meses
        juros_price = total_pago_price - valor
    except: pmt_price = 0; juros_price = 0

    # SAC
    try:
        amort = valor / meses
        pmt_sac_ini = amort + (valor * i)
        pmt_sac_fim = amort + (amort * i)
        total_pago_sac = (pmt_sac_ini + pmt_sac_fim) * meses / 2
        juros_sac = total_pago_sac - valor
    except: pmt_sac_ini = 0; pmt_sac_fim = 0; juros_sac = 0
    
    return {
        "SAC": {"primeira": pmt_sac_ini, "ultima": pmt_sac_fim, "juros": juros_sac},
        "PRICE": {"parcela": pmt_price, "juros": juros_price}
    }

def calcular_parcela_financiamento(valor_financiado, meses, taxa_anual_pct, sistema):
    if valor_financiado is None or valor_financiado <= 0 or meses <= 0: return 0.0
    i_mensal = (1 + taxa_anual_pct/100)**(1/12) - 1
    if sistema == "PRICE":
        try: return valor_financiado * (i_mensal * (1 + i_mensal)**meses) / ((1 + i_mensal)**meses - 1)
        except: return 0.0
    else:
        amortizacao = valor_financiado / meses
        juros = valor_financiado * i_mensal
        return amortizacao + juros

def formatar_link_drive(url):
    """
    Retorna apenas a URL direta se for Google Drive para usar no modal customizado.
    """
    if "drive.google.com" in url and "/d/" in url:
        try:
            file_id = url.split("/d/")[1].split("/")[0]
            # Link direto para visualização raw (export=view)
            full_link = f"https://drive.google.com/uc?export=view&id={file_id}"
            return full_link
        except:
            return url
    return url

def scroll_to_top():
    scroll_to_top_component()

# =============================================================================
# 1. CARREGAMENTO DE DADOS
# =============================================================================

@st.cache_data(ttl=300)
def carregar_dados_sistema():
    try:
        from simulador_dv.services.sistema_data import load_sistema_dataframes

        return load_sistema_dataframes()
    except Exception as e:
        st.error(f"Erro dados: {e}")
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            dict(DEFAULT_PREMISSAS),
        )

# =============================================================================
# 2. MOTOR E FUNÇÕES
# =============================================================================

def configurar_layout():
    favicon = URL_FAVICON_RESERVA
    if os.path.exists("favicon.png") and Image:
        try: favicon = Image.open("favicon.png")
        except: pass
    st.set_page_config(page_title="Simulador Direcional Elite", page_icon=favicon, layout="wide")

    # CSS externo: simulador_dv/assets/css/*.css (ver simulador_dv/ui/inject.py)
    inject_streamlit_styles()

def render_stepper(current_step_name):
    steps = [
        {"id": "input", "label": "Dados"},
        {"id": "fechamento_aprovado", "label": "Fechamento"},
        {"id": "guide", "label": "Análise"},
        {"id": "selection", "label": "Imóvel"},
        {"id": "payment_flow", "label": "Pagamento"},
        {"id": "summary", "label": "Resumo"}
    ]
    current_idx = 0
    for i, s in enumerate(steps):
        if s["id"] == current_step_name:
            current_idx = i
            break
    
    html = '<div class="stepper-container"><div class="stepper-line-bg"></div>'
    for i, step in enumerate(steps):
        status_class = ""
        icon_content = str(i + 1)
        if i < current_idx:
            status_class = "completed"
            icon_content = "✓"
        elif i == current_idx:
            status_class = "active"
        html += f"""<div class="stepper-step {status_class}">
    <div class="step-bubble">{icon_content}</div>
    <div class="step-label">{step['label']}</div>
</div>"""
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

def tela_login(df_logins):
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<br><br><h3 style='text-align:center;'>LOGIN</h3>", unsafe_allow_html=True)
        # Envelopando em form para submissão com Enter
        with st.form("login_form"):
            email = st.text_input("E-mail", key="login_email")
            senha = st.text_input("Senha", type="password", key="login_pass")
            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("ACESSAR SISTEMA", type="primary", use_container_width=True)
            
        if submitted:
            if df_logins.empty: st.error("Base de usuários vazia.")
            else:
                user = df_logins[(df_logins['Email'] == email.strip().lower()) & (df_logins['Senha'] == senha.strip())]
                if not user.empty:
                    data = user.iloc[0]
                    st.session_state.update({
                        'logged_in': True, 'user_email': email,
                        'user_name': str(data.get('Nome', '')).strip(),
                        'user_imobiliaria': str(data.get('Imobiliaria', 'Geral')).strip(),
                        'user_cargo': str(data.get('Cargo', '')).strip(),
                        'user_phone': str(data.get('Telefone', '')).strip() # Salva telefone
                    })
                    st.success("Login realizado!"); st.rerun()
                else: st.error("Credenciais inválidas.")

@st.dialog("Opções de Exportação")
def show_export_dialog(d):
    # Alterado para text-align: center para alinhar com o tema
    st.markdown(f"<h3 style='text-align: center; color: {COR_AZUL_ESC}; margin: 0;'>Resumo da Simulação</h3>", unsafe_allow_html=True)
    st.markdown("Escolha como deseja exportar o documento.")
    
    # Injetar dados do corretor no dicionário para o PDF
    d['corretor_nome'] = st.session_state.get('user_name', '')
    d['corretor_email'] = st.session_state.get('user_email', '')
    d['corretor_telefone'] = st.session_state.get('user_phone', '')
    
    pdf_data = gerar_resumo_pdf(d)

    if pdf_data:
        st.download_button(label="Baixar PDF", data=pdf_data, file_name=f"Resumo_Direcional_{d.get('nome', 'Cliente')}.pdf", mime="application/pdf", use_container_width=True)
    else:
        st.warning("Geração de PDF indisponível.")

    st.markdown("---")
    st.markdown("**Enviar por E-mail (Cliente)**")
    email = st.text_input("Endereço de e-mail do cliente", placeholder="cliente@exemplo.com")
    if st.button("Enviar Email para Cliente", use_container_width=True):
        if email and "@" in email:
            # Passando DADOS COMPLETOS para o email HTML e tipo CLIENTE
            sucesso, msg = enviar_email_smtp(email, d.get('nome', 'Cliente'), pdf_data, d, tipo='cliente')
            if sucesso: st.success(msg)
            else: st.error(msg)
        else:
            st.error("E-mail inválido")

# =============================================================================
# APLICAÇÃO PRINCIPAL
# =============================================================================

@st.dialog("Cadastrar Novo Cliente")
def dialog_novo_cliente(motor):
    # Formulário de Cadastro de Novo Cliente
    st.markdown("Preencha os dados do cliente para iniciar a simulação.")
    st.markdown('<div style="max-height: 65vh; overflow-y: auto; padding-right: 10px;">', unsafe_allow_html=True)
    
    # Recuperar valores da sessão ou usar defaults
    curr_nome = st.session_state.dados_cliente.get('nome', "")
    curr_cpf = st.session_state.dados_cliente.get('cpf', "")
    
    with st.form("form_cadastro"):
        nome = st.text_input("Nome Completo", value=curr_nome, placeholder="Nome Completo", key="in_nome_v28")
        
        # --- LÓGICA DE MÁSCARA AUTOMÁTICA DE CPF NO CARREGAMENTO ---
        # Se o CPF já existe no estado, aplicamos a máscara para exibição
        if curr_cpf:
            curr_cpf = aplicar_mascara_cpf(curr_cpf)
            
        cpf_val = st.text_input("CPF", value=curr_cpf, placeholder="000.000.000-00", key="in_cpf_v3", max_chars=14)
        
        d_nasc_default = st.session_state.dados_cliente.get('data_nascimento', date(1990, 1, 1))
        if isinstance(d_nasc_default, str):
            try: d_nasc_default = datetime.strptime(d_nasc_default, '%Y-%m-%d').date()
            except: 
                try: d_nasc_default = datetime.strptime(d_nasc_default, '%d/%m/%Y').date()
                except: d_nasc_default = date(1990, 1, 1)

        data_nasc = st.date_input("Data de Nascimento", value=d_nasc_default, min_value=date(1900, 1, 1), max_value=datetime.now().date(), format="DD/MM/YYYY", key="in_dt_nasc_v3")

        st.markdown("---")
        qtd_part = st.number_input("Participantes na Renda", min_value=1, max_value=4, value=st.session_state.dados_cliente.get('qtd_participantes', 1), step=1, key="qtd_part_v3")

        cols_renda = st.columns(qtd_part)
        lista_rendas_input = []
        rendas_anteriores = st.session_state.dados_cliente.get('rendas_lista', [])
        
        # Helper to clear input on empty
        def get_val(idx, default):
            v = float(rendas_anteriores[idx]) if idx < len(rendas_anteriores) else default
            return None if v == 0.0 else v

        for i in range(qtd_part):
            with cols_renda[i]:
                def_val = 3500.0 if i == 0 and not rendas_anteriores else 0.0
                current_val = get_val(i, def_val)
                # Use value=None if 0.0 to show placeholder "0,00"
                val_display = None if current_val == 0.0 else current_val
                
                val_r = st.number_input(f"Renda Part. {i+1}", min_value=0.0, value=val_display, step=100.0, key=f"renda_part_{i}_v3", placeholder="0,00", format="%.2f")
                lista_rendas_input.append(val_r)

        rank_opts = ["DIAMANTE", "OURO", "PRATA", "BRONZE", "AÇO"]
        curr_ranking = st.session_state.dados_cliente.get('ranking', "DIAMANTE")
        idx_ranking = rank_opts.index(curr_ranking) if curr_ranking in rank_opts else 0
        ranking = st.selectbox("Ranking do Cliente", options=rank_opts, index=idx_ranking, key="in_rank_v28")
        
        politica_ps = st.selectbox("Política de Pro Soluto", ["Direcional", "Emcash"], index=0 if st.session_state.dados_cliente.get('politica') != "Emcash" else 1, key="in_pol_v28")
        social = st.toggle("Fator Social", value=st.session_state.dados_cliente.get('social', False), key="in_soc_v28")
        cotista = st.toggle("Cotista FGTS", value=st.session_state.dados_cliente.get('cotista', True), key="in_cot_v28")

        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("Confirmar e Avançar", type="primary", use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

    if submitted:
        # Calcular renda total dentro do submit
        renda_total_calc = sum([r if r is not None else 0.0 for r in lista_rendas_input])
        
        # Validação básica
        if not nome.strip(): st.error("Por favor, informe o Nome do Cliente."); return
        if not cpf_val.strip(): st.error("Por favor, informe o CPF do Cliente."); return
        
        # Aplicar formatação automática do CPF ao salvar (garantia)
        cpf_formatado = aplicar_mascara_cpf(cpf_val)
        
        if not validar_cpf(cpf_val): st.error("CPF Inválido."); return
        if renda_total_calc <= 0: st.error("A renda total deve ser maior que zero."); return

        # Salvar estado
        st.session_state.dados_cliente.update({
            'nome': nome, 
            'cpf': limpar_cpf_visual(cpf_formatado), 
            'data_nascimento': data_nasc, 
            'renda': renda_total_calc, 
            'rendas_lista': [r if r is not None else 0.0 for r in lista_rendas_input],
            'social': social, 
            'cotista': cotista, 
            'ranking': ranking, 
            'politica': politica_ps,
            'qtd_participantes': qtd_part,
            # Limpar históricos se for novo cliente
            'finan_usado_historico': 0.0,
            'ps_usado_historico': 0.0,
            'fgts_usado_historico': 0.0
        })

        # Processar lógica de negócio (enquadramento inicial)
        prazo_ps_max = 66 if politica_ps == "Emcash" else 84
        limit_ps_r = 0.30
        f_faixa_ref, s_faixa_ref, fx_nome_ref = motor.obter_enquadramento(renda_total_calc, social, cotista, valor_avaliacao=240000)

        st.session_state.dados_cliente.update({
            'prazo_ps_max': prazo_ps_max,
            'limit_ps_renda': limit_ps_r, 
            'finan_f_ref': f_faixa_ref, 
            'sub_f_ref': s_faixa_ref
        })
        
        # NÃO AVANÇAR AUTOMATICAMENTE - Manter em 'input' mas marcar cliente como ativo
        # st.session_state.passo_simulacao = 'guide' 
        st.session_state.cliente_ativo = True
        st.rerun()

@st.dialog("Buscar Cliente Cadastrado", width="large")
def dialog_buscar_cliente(df_cadastros, motor):
    if df_cadastros.empty:
        st.warning("A base de clientes está vazia.")
        return

    # Campo de busca
    search_query = st.text_input("Buscar por Nome ou CPF", placeholder="Digite para filtrar...")
    
    # Lista de clientes filtrada
    filtered_df = df_cadastros.copy()
    if 'Nome' in filtered_df.columns:
        filtered_df = filtered_df.sort_values('Nome')
        
    if search_query:
        # Filtrar por nome ou CPF
        term = search_query.lower()
        mask = filtered_df['Nome'].astype(str).str.lower().str.contains(term)
        if 'CPF' in filtered_df.columns:
            mask = mask | filtered_df['CPF'].astype(str).str.contains(term)
        filtered_df = filtered_df[mask]

    # Container com scroll para lista - Aumentado altura para notebooks
    st.markdown('<div style="max-height: 60vh; overflow-y: auto; padding-right: 5px;">', unsafe_allow_html=True)
    
    if filtered_df.empty:
        st.info("Nenhum cliente encontrado.")
    else:
        for idx, row in filtered_df.iterrows():
            c_nome = row.get('Nome', 'Sem Nome')
            c_cpf = formatar_cpf_saida(row.get('CPF', ''))
            label_btn = f"{c_nome} - {c_cpf}"
            
            if st.button(label_btn, key=f"btn_cli_{idx}", use_container_width=True):
                 # Carregar dados e avançar
                row_cli = row
                
                # Helper para extrair float
                def safe_get_float_row(r, k):
                    return safe_float_convert(r.get(k, 0))
                
                # Carregar dados na sessão
                rs_load = [safe_get_float_row(row_cli, f'Renda Part. {i}') for i in range(1, 5)]
                qtd_p_load = 1
                for i in range(4, 0, -1):
                    if rs_load[i-1] > 0:
                        qtd_p_load = i
                        break
                
                # Calcula o total da renda
                renda_total_calc = sum(rs_load)

                # Helper para data
                dn_load = row_cli.get('Data de Nascimento')
                try:
                    if isinstance(dn_load, str):
                        dn_load = datetime.strptime(dn_load, '%Y-%m-%d').date()
                except:
                    dn_load = date(1990, 1, 1)

                ranking = row_cli.get('Ranking')
                politica_ps = row_cli.get('Política de Pro Soluto')
                social = str(row_cli.get('Fator Social', '')).lower() == 'sim'
                cotista = str(row_cli.get('Cotista FGTS', '')).lower() == 'sim'

                st.session_state.dados_cliente.update({
                    'nome': row_cli.get('Nome'),
                    'cpf': row_cli.get('CPF'),
                    'data_nascimento': dn_load,
                    'qtd_participantes': qtd_p_load,
                    'rendas_lista': rs_load,
                    'renda': renda_total_calc,
                    'ranking': ranking,
                    'politica': politica_ps,
                    'social': social,
                    'cotista': cotista
                })

                # Processar lógica de negócio (enquadramento inicial)
                prazo_ps_max = 66 if politica_ps == "Emcash" else 84
                limit_ps_r = 0.30
                f_faixa_ref, s_faixa_ref, fx_nome_ref = motor.obter_enquadramento(renda_total_calc, social, cotista, valor_avaliacao=240000)

                st.session_state.dados_cliente.update({
                    'prazo_ps_max': prazo_ps_max,
                    'limit_ps_renda': limit_ps_r, 
                    'finan_f_ref': f_faixa_ref, 
                    'sub_f_ref': s_faixa_ref
                })

                st.toast(f"Dados de {c_nome} carregados!", icon="✅")
                # NÃO AVANÇAR AUTOMATICAMENTE
                # st.session_state.passo_simulacao = 'guide'
                st.session_state.cliente_ativo = True
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

def aba_simulador_automacao(df_finan, df_estoque, df_politicas, df_cadastros, premissas_dict=None):
    passo = st.session_state.get('passo_simulacao', 'input')
    motor = MotorRecomendacao(df_finan, df_estoque, df_politicas)
    _prem = dict(DEFAULT_PREMISSAS)
    if premissas_dict:
        _prem.update(premissas_dict)

    def taxa_fin_vigente(d_cli):
        return resolver_taxa_financiamento_anual_pct(d_cli or {}, _prem)
    if 'dados_cliente' not in st.session_state: st.session_state.dados_cliente = {}

    # --- SIDEBAR PERFIL (ATUALIZADA) ---
    with st.sidebar:
        user_name = st.session_state.get('user_name', 'Corretor').upper()
        user_cargo = st.session_state.get('user_cargo', 'Consultor').upper()
        user_imob = st.session_state.get('user_imobiliaria', 'Direcional').upper()

        st.markdown(f"""
        <div class="sidebar-profile">
            <div class="profile-avatar">{user_name[0] if user_name else 'C'}</div>
            <div class="profile-name" style="font-weight: 800; color: {COR_AZUL_ESC}; font-size: 1.1rem; margin-bottom: 5px;">{user_name}</div>
            <div class="profile-role" style="color: {COR_VERMELHO}; font-weight: 700; font-size: 0.9rem;">{user_cargo}</div>
            <div class="profile-sub" style="color: {COR_AZUL_ESC}; font-size: 0.85rem;">{user_imob}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### Navegação")
        if st.button("Simulador", use_container_width=True):
            st.session_state.passo_simulacao = 'input'
            st.rerun()
        if st.button("Galeria de Produtos", use_container_width=True):
            st.session_state.passo_simulacao = 'gallery'
            st.rerun()

        st.markdown("---")
        st.markdown("#### Histórico de Simulações")

        search_term = st.text_input("Buscar cliente...", placeholder="Digite o nome", label_visibility="collapsed")

        try:
            df_h = df_cadastros.copy()
            if not df_h.empty:
                col_corretor = next((c for c in df_h.columns if 'Nome do Corretor' in c), None)
                col_nome_cliente = next((c for c in df_h.columns if c == 'Nome'), None)
                col_data_sim = next((c for c in df_h.columns if 'Data' in c and '/' in str(df_h[c].iloc[0])), None)

                if col_corretor:
                    my_hist = df_h[df_h[col_corretor].astype(str).str.strip().str.upper() == user_name.strip()]
                    if search_term and col_nome_cliente:
                        my_hist = my_hist[my_hist[col_nome_cliente].astype(str).str.contains(search_term, case=False, na=False)]
                    my_hist = my_hist.tail(15).iloc[::-1]

                    if not my_hist.empty:
                        for idx, row in my_hist.iterrows():
                            c_nome = row.get('Nome', 'Cli')
                            c_emp = row.get('Empreendimento Final', 'Emp')
                            c_data = ""
                            if col_data_sim and pd.notnull(row.get(col_data_sim)):
                                try: c_data = str(row.get(col_data_sim)).split('.')[0]
                                except: pass

                            label = f"{c_nome} | {c_emp}"
                            if c_data: label += f" | {c_data}"

                            if st.button(label, key=f"hist_{idx}", use_container_width=True):
                                # Helper para tratamento seguro de floats
                                def safe_get_float(r, k):
                                    return safe_float_convert(r.get(k, 0))
                                
                                # FIX CPF: Remove .0 e zfill 11
                                def fix_cpf_from_row(val):
                                    return limpar_cpf_visual(val)

                                # Reconstrução de Rendas e Participantes
                                rs = [safe_get_float(row, f'Renda Part. {i}') for i in range(1, 5)]
                                qtd_p = 1
                                for i in range(4, 0, -1):
                                    if rs[i-1] > 0:
                                        qtd_p = i
                                        break
                                
                                # Calcula o total da renda (CORREÇÃO DO BUG R$ 0,00)
                                renda_total = sum(rs)

                                soc = str(row.get('Fator Social', '')).strip().lower() in ['sim', 's', 'true']
                                cot = str(row.get('Cotista FGTS', '')).strip().lower() in ['sim', 's', 'true']
                                
                                # Recupera Sistema de Amortização com fallback
                                sist_amort = row.get('Sistema de Amortização', 'SAC')
                                if pd.isnull(sist_amort) or str(sist_amort).strip() == '':
                                     sist_amort = 'SAC'

                                st.session_state.dados_cliente = {
                                    'nome': row.get('Nome'), 
                                    'cpf': fix_cpf_from_row(row.get('CPF')),
                                    'data_nascimento': row.get('Data de Nascimento'),
                                    'qtd_participantes': qtd_p,
                                    'rendas_lista': rs,
                                    'renda': renda_total,  # Chave adicionada explicitamente
                                    'ranking': row.get('Ranking'),
                                    'politica': row.get('Política de Pro Soluto'),
                                    'social': soc,
                                    'cotista': cot,
                                    
                                    'empreendimento_nome': row.get('Empreendimento Final'),
                                    'unidade_id': row.get('Unidade Final'),
                                    'imovel_valor': safe_get_float(row, 'Preço Unidade Final'),
                                    'finan_estimado': safe_get_float(row, 'Financiamento Aprovado'),
                                    'fgts_sub': safe_get_float(row, 'Subsídio Máximo'),
                                    
                                    'finan_usado': safe_get_float(row, 'Financiamento Final'),
                                    'fgts_sub_usado': safe_get_float(row, 'FGTS + Subsídio Final'),
                                    'ps_usado': safe_get_float(row, 'Pro Soluto Final'),
                                    'ps_parcelas': int(float(str(row.get('Número de Parcelas do Pro Soluto', 0)).replace(',','.'))),
                                    'ps_mensal': safe_get_float(row, 'Mensalidade PS'),
                                    'ato_final': safe_get_float(row, 'Ato'),
                                    'ato_30': safe_get_float(row, 'Ato 30'),
                                    'ato_60': safe_get_float(row, 'Ato 60'),
                                    'ato_90': safe_get_float(row, 'Ato 90'),
                                    'prazo_financiamento': int(float(str(row.get('Prazo Financiamento', 360)).replace(',','.'))) if row.get('Prazo Financiamento') else 360,
                                    'sistema_amortizacao': sist_amort # Recupera sistema
                                }
                                
                                st.session_state.dados_cliente['entrada_total'] = sum([
                                    st.session_state.dados_cliente['ato_final'],
                                    st.session_state.dados_cliente['ato_30'],
                                    st.session_state.dados_cliente['ato_60'],
                                    st.session_state.dados_cliente['ato_90']
                                ])

                                keys_to_reset = [
                                    'in_nome_v28', 'in_cpf_v3', 'in_dt_nasc_v3', 'in_genero_v3', 
                                    'qtd_part_v3', 'in_rank_v28', 'in_pol_v28', 'in_soc_v28', 'in_cot_v28',
                                    'fin_u_key', 'fgts_u_key', 'ps_u_key', 'parc_ps_key', 
                                    'ato_1_key', 'ato_2_key', 'ato_3_key', 'ato_4_key', 'volta_caixa_key'
                                ]
                                for i in range(5): keys_to_reset.append(f"renda_part_{i}_v3")
                                for k in keys_to_reset:
                                    if k in st.session_state: del st.session_state[k]

                                st.session_state.passo_simulacao = 'client_analytics'
                                st.session_state.cliente_ativo = True
                                scroll_to_top()
                                st.rerun()
                    else: st.caption("Nenhum histórico recente.")
                else: st.caption("Coluna de corretor não encontrada.")
            else: st.caption("Sem dados cadastrados.")
        except Exception as e: st.caption(f"Erro histórico: {str(e)}")

    # RENDER PROGRESS BAR
    if passo != 'client_analytics' and passo != 'gallery':
        render_stepper(passo)
        
    # --- GALERIA DE PRODUTOS ---
    if passo == 'gallery':
        st.markdown("### Galeria de Produtos")
        st.markdown("---")
        
        # Obter lista de produtos
        lista_produtos = sorted(list(CATALOGO_PRODUTOS.keys()))
        
        # TABS PARA SELEÇÃO HORIZONTAL (SLIDER-LIKE)
        if not lista_produtos:
            st.warning("Nenhum produto cadastrado na galeria.")
        else:
            # HTML + JS externos: simulador_dv/assets/html|js/gallery_modal.*
            inject_gallery_modal()

            tabs_produtos = st.tabs(lista_produtos)
            
            for aba, prod_key in zip(tabs_produtos, lista_produtos):
                with aba:
                    # Recupera metadados
                    meta = CATALOGO_PRODUTOS[prod_key]
                    
                    st.markdown(f"#### {prod_key}")
                    
                    # SEÇÃO 1: VÍDEO E MAPA (Lado a Lado 50/50)
                    col_vid, col_map = st.columns(2)
                    
                    with col_vid:
                        if meta.get("video"):
                            st.video(meta["video"])
                        else:
                            st.info("Vídeo indisponível.")
                            
                    with col_map:
                        if meta.get("lat") and meta.get("lon"):
                            # Mapa Folium com OpenStreetMap (Mostra ruas e referências)
                            m = folium.Map(location=[meta['lat'], meta['lon']], zoom_start=15, tiles="OpenStreetMap")
                            folium.Marker(
                                [meta['lat'], meta['lon']], 
                                popup=prod_key, 
                                tooltip=prod_key,
                                icon=folium.Icon(color="red", icon="home")
                            ).add_to(m)
                            
                            # Renderiza o mapa com altura fixa para alinhar com o vídeo
                            st_folium(m, height=360, use_container_width=True)
                        else:
                            st.info("Mapa indisponível.")
                    
                    st.markdown("---")

                    # --- BOX DE INFORMAÇÕES (NOVO) ---
                    if not df_estoque.empty and 'Empreendimento' in df_estoque.columns:
                        df_emp_info = df_estoque[df_estoque['Empreendimento'] == prod_key]
                        if not df_emp_info.empty:
                            # Cálculos
                            min_p = df_emp_info['Valor de Venda'].min()
                            max_p = df_emp_info['Valor de Venda'].max()
                            var_preco = f"R$ {fmt_br(min_p)} a R$ {fmt_br(max_p)}"
                            
                            areas_vals = []
                            if 'Area' in df_emp_info.columns:
                                areas_vals = pd.to_numeric(df_emp_info['Area'], errors='coerce').dropna()
                            
                            if not areas_vals.empty:
                                min_area = areas_vals.min()
                                max_area = areas_vals.max()
                                metragem_txt = f"{min_area}m² a {max_area}m²"
                                
                                # Cálculo preço m2
                                min_m2 = min_p / max_area if max_area > 0 else 0
                                max_m2 = max_p / min_area if min_area > 0 else 0
                                var_m2 = f"R$ {fmt_br(min_m2)} a R$ {fmt_br(max_m2)}"
                            else:
                                metragem_txt = "N/A"
                                var_m2 = "N/A"
                            
                            num_unidades = len(df_emp_info)
                            num_blocos = df_emp_info['Bloco_Sort'].nunique() if 'Bloco_Sort' in df_emp_info.columns else 1
                            
                            bairro_info = df_emp_info['Bairro'].iloc[0] if 'Bairro' in df_emp_info.columns else "N/A"
                            endereco_info = df_emp_info['Endereco'].iloc[0] if 'Endereco' in df_emp_info.columns else "N/A"
                            entrega_info = df_emp_info['Data Entrega'].iloc[0] if 'Data Entrega' in df_emp_info.columns else "N/A"
                            
                            st.markdown(f"""
                            <div class="summary-body" style="padding: 20px; margin-bottom: 20px;">
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                                    <div><small style="color:#64748b; font-weight:bold;">VARIAÇÃO PREÇO</small><br><span style="color:{COR_AZUL_ESC}; font-weight:bold;">{var_preco}</span></div>
                                    <div><small style="color:#64748b; font-weight:bold;">METRAGEM</small><br><span style="color:{COR_AZUL_ESC}; font-weight:bold;">{metragem_txt}</span></div>
                                    <div><small style="color:#64748b; font-weight:bold;">PREÇO M²</small><br><span style="color:{COR_AZUL_ESC}; font-weight:bold;">{var_m2}</span></div>
                                    <div><small style="color:#64748b; font-weight:bold;">ENTREGA</small><br><span style="color:{COR_AZUL_ESC}; font-weight:bold;">{entrega_info}</span></div>
                                    <div><small style="color:#64748b; font-weight:bold;">BLOCOS / UNID.</small><br><span style="color:{COR_AZUL_ESC}; font-weight:bold;">{num_blocos} / {num_unidades}</span></div>
                                    <div><small style="color:#64748b; font-weight:bold;">BAIRRO</small><br><span style="color:{COR_AZUL_ESC}; font-weight:bold;">{bairro_info}</span></div>
                                </div>
                                <div style="margin-top: 15px; border-top: 1px solid #e2e8f0; padding-top: 10px;">
                                    <small style="color:#64748b; font-weight:bold;">ENDEREÇO</small><br><span style="color:{COR_AZUL_ESC};">{endereco_info}</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    # Organizar imagens por categoria (Seções Verticais)
                    imagens_raw = meta.get("imagens", [])
                    categorias = {"MAPA": [], "MASTERPLAN": [], "PLANTAS": [], "IMAGENS ILUSTRATIVAS": []}
                    link_ficha = None
                    
                    # Prepara array global de imagens para o slider JS
                    all_images_links = []

                    for item in imagens_raw:
                        nome_up = item['nome'].upper()
                        # Identificar Ficha Técnica
                        if "FICHA" in nome_up or "PDF" in nome_up:
                            link_ficha = item['link']
                            continue
                        
                        # Extrair link direto
                        full_link = formatar_link_drive(item['link'])
                        
                        # Adicionar a lista global para navegação nas setas
                        # (Opcional: se quiser navegar só dentro da categoria, mudar logica. Aqui navega em tudo)
                        # Vou colocar na ordem de exibição abaixo
                        
                        # Categorizar
                        if "MAPA" in nome_up:
                            categorias["MAPA"].append((item, full_link))
                        elif "MASTERPLAN" in nome_up:
                            categorias["MASTERPLAN"].append((item, full_link))
                        elif "PLANTA" in nome_up:
                            categorias["PLANTAS"].append((item, full_link))
                        else:
                            categorias["IMAGENS ILUSTRATIVAS"].append((item, full_link))

                    # Construir lista ordenada final de links para o JS
                    # Ordem: Mapa -> Masterplan -> Plantas -> Imagens
                    ordered_links = []
                    for cat in ["MAPA", "MASTERPLAN", "PLANTAS", "IMAGENS ILUSTRATIVAS"]:
                        for _, link in categorias[cat]:
                            ordered_links.append(link)
                    
                    # Serializar para JSON para passar ao JS
                    json_links = json.dumps(ordered_links)
                    
                    # Função auxiliar para renderizar HTML de imagem
                    def render_img_html(img_list, start_index):
                        html = '<div class="scrolling-images">'
                        local_idx = start_index
                        for item, link in img_list:
                            # Thumbnail usa o link direto mesmo para simplicidade ou gerador de thumb se existir
                            # Aqui usando full link no src, browser faz cache. Se for pesado, ideal seria thumb.
                            # Mas o formatar_link_drive retorna full para o modal.
                            # Para src da img tag, se for drive, podemos tentar thumbnail.
                            
                            # Tentar reconstruir thumb se for drive
                            thumb_src = link
                            if "drive.google.com/uc?export=view&id=" in link:
                                fid = link.split("id=")[1]
                                thumb_src = f"https://drive.google.com/thumbnail?id={fid}&sz=w600"

                            # Masterplan placeholder
                            if "MASTERPLAN" in item['nome'].upper():
                                html += f'''
                                <div class="masterplan-placeholder" onclick='openGallery({json_links}, {local_idx})'>
                                    <div style="font-size: 3rem; margin-bottom: 10px;">🗺️</div>
                                    <div>MASTERPLAN</div>
                                    <div style="font-size: 0.7rem; font-weight: 400; margin-top: 5px;">Clique para ampliar</div>
                                </div>
                                '''
                            else:
                                html += f'''<img src="{thumb_src}" alt="{item["nome"]}" title="{item["nome"]}" onclick='openGallery({json_links}, {local_idx})'>'''
                            local_idx += 1
                        html += '</div>'
                        return html, local_idx

                    # Renderizar Seções
                    current_global_index = 0
                    
                    if categorias["MAPA"]:
                        st.markdown("##### Localização")
                        html_content, current_global_index = render_img_html(categorias["MAPA"], current_global_index)
                        st.markdown(html_content, unsafe_allow_html=True)

                    if categorias["MASTERPLAN"]:
                        st.markdown("##### Masterplan")
                        html_content, current_global_index = render_img_html(categorias["MASTERPLAN"], current_global_index)
                        st.markdown(html_content, unsafe_allow_html=True)

                    if categorias["PLANTAS"]:
                        st.markdown("##### Plantas")
                        html_content, current_global_index = render_img_html(categorias["PLANTAS"], current_global_index)
                        st.markdown(html_content, unsafe_allow_html=True)
                        
                    if categorias["IMAGENS ILUSTRATIVAS"]:
                        st.markdown("##### Imagens Ilustrativas")
                        html_content, current_global_index = render_img_html(categorias["IMAGENS ILUSTRATIVAS"], current_global_index)
                        st.markdown(html_content, unsafe_allow_html=True)

                    st.markdown("---")
                    
                    # SEÇÃO 4: FICHA TÉCNICA (BOTÃO CENTRALIZADO)
                    if link_ficha:
                        c1, c2, c3 = st.columns([1, 2, 1])
                        with c2:
                            st.link_button("BAIXAR FICHA TÉCNICA", link_ficha, use_container_width=True)

    # --- ABA ANALYTICS (SECURE TAB - ALTAIR) ---
    elif passo == 'client_analytics':
        d = st.session_state.dados_cliente
        
        st.markdown(f"### Painel do Cliente: {d.get('nome', 'Não Informado')}")

        # --- SEÇÃO 1: FICHA DO CLIENTE ---
        with st.container():
            col1, col2, col3 = st.columns(3)
            
            # Format Data Nascimento
            dn = str(d.get('data_nascimento', ''))
            if '-' in dn:
                try: dn = datetime.strptime(dn, '%Y-%m-%d').strftime('%d/%m/%Y')
                except: pass
            
            # Format CPF
            cpf_show = d.get('cpf', '')
            if len(cpf_show) == 11:
                cpf_show = f"{cpf_show[:3]}.{cpf_show[3:6]}.{cpf_show[6:9]}-{cpf_show[9:]}"

            with col1:
                st.markdown(f"""
                <div class="hover-card" style="border-left: 5px solid {COR_AZUL_ESC};">
                    <p style="font-weight: bold; margin-bottom: 10px; color: {COR_AZUL_ESC};">Dados Pessoais</p>
                    <p style="font-size: 0.9rem; margin: 0;">CPF: {cpf_show}</p>
                    <p style="font-size: 0.9rem; margin: 0;">Nascimento: {dn}</p>
                    <p style="font-size: 0.9rem; margin: 0;">Ranking: {d.get('ranking')}</p>
                </div>""", unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="hover-card" style="border-left: 5px solid {COR_AZUL_ESC};">
                    <p style="font-weight: bold; margin-bottom: 10px; color: {COR_AZUL_ESC};">Renda & Perfil</p>
                    <p style="font-size: 0.9rem; margin: 0;">Renda Familiar: R$ {fmt_br(d.get('renda', 0))}</p>
                    <p style="font-size: 0.9rem; margin: 0;">Participantes: {d.get('qtd_participantes')}</p>
                    <p style="font-size: 0.9rem; margin: 0;">FGTS: {'Sim' if d.get('cotista') else 'Não'} | Social: {'Sim' if d.get('social') else 'Não'}</p>
                </div>""", unsafe_allow_html=True)
            with col3:
                st.markdown(f"""
                <div class="hover-card" style="border-left: 5px solid {COR_AZUL_ESC};">
                    <p style="font-weight: bold; margin-bottom: 10px; color: {COR_AZUL_ESC};">Imóvel Salvo</p>
                    <p style="font-size: 0.9rem; margin: 0;">{d.get('empreendimento_nome')}</p>
                    <p style="font-size: 0.9rem; margin: 0;">Unidade: {d.get('unidade_id')}</p>
                    <p style="font-size: 0.9rem; margin: 0;">Valor: <span style='color:{COR_VERMELHO}; font-weight:bold;'>R$ {fmt_br(d.get('imovel_valor', 0))}</span></p>
                </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # --- SEÇÃO 2: GRÁFICOS DE PIZZA (COMPOSIÇÃO) ---
        g_col1, g_col2 = st.columns(2)
        
        # Gráfico 1: Composição da Compra
        with g_col1:
            st.markdown("##### Composição da Compra")
            labels = ['Ato', '30 Dias', '60 Dias', '90 Dias', 'Pro Soluto', 'Financiamento', 'FGTS/Subsídio']
            values = [
                d.get('ato_final', 0), d.get('ato_30', 0), d.get('ato_60', 0), d.get('ato_90', 0),
                d.get('ps_usado', 0), d.get('finan_usado', 0), d.get('fgts_sub_usado', 0)
            ]
            
            # Filter zeros for cleaner chart
            clean_data = [(l, v) for l, v in zip(labels, values) if v > 0]
            if clean_data:
                df_pie = pd.DataFrame(clean_data, columns=['Tipo', 'Valor'])
                
                # Define cores personalizadas para cada tipo de pagamento
                color_scale = alt.Scale(domain=['Ato', '30 Dias', '60 Dias', '90 Dias', 'Pro Soluto', 'Financiamento', 'FGTS/Subsídio'],
                                                                  range=['#e30613', '#c0392b', '#94a3b8', '#64748b', '#f59e0b', '#002c5d', '#10b981'])

                # Selection for interactivity
                hover = alt.selection_point(on='mouseover', empty=False, fields=['Tipo'])

                base = alt.Chart(df_pie).encode(theta=alt.Theta("Valor", stack=True))
                pie = base.mark_arc(innerRadius=60, outerRadius=120).encode(
                    color=alt.Color("Tipo", scale=color_scale, legend=None),
                    order=alt.Order("Valor", sort="descending"),
                    tooltip=[alt.Tooltip("Tipo"), alt.Tooltip("Valor", format=",.2f")],
                    opacity=alt.condition(hover, alt.value(1), alt.value(0.7)),
                    stroke=alt.condition(hover, alt.value('white'), alt.value(None)),
                    strokeWidth=alt.condition(hover, alt.value(2), alt.value(0))
                ).add_params(hover)
                
                text = base.mark_text(radius=140).encode(
                    text=alt.Text("Valor", format=",.2f"),
                    order=alt.Order("Valor", sort="descending"),
                    color=alt.value(COR_AZUL_ESC)  
                )
                
                final_pie = pie.encode(color=alt.Color("Tipo", scale=color_scale, legend=alt.Legend(orient="bottom", columns=2, title=None))).configure_view(strokeWidth=0).configure_axis(grid=False, domain=False)
                st.altair_chart(final_pie, use_container_width=True)
            else:
                st.info("Sem dados financeiros suficientes.")

        # Gráfico 2: Composição de Renda
        with g_col2:
            st.markdown("##### Composição de Renda")
            rendas = d.get('rendas_lista', [])
            pie_renda = [(f"Part. {i+1}", r) for i, r in enumerate(rendas) if r > 0]
            if pie_renda:
                df_renda = pd.DataFrame(pie_renda, columns=['Participante', 'Renda'])
                
                color_scale_renda = alt.Scale(domain=[f"Part. {i+1}" for i in range(len(pie_renda))],
                                                                  range=['#002c5d', '#e30613', '#f59e0b', '#10b981'])

                hover_renda = alt.selection_point(on='mouseover', empty=False, fields=['Participante'])

                base = alt.Chart(df_renda).encode(theta=alt.Theta("Renda", stack=True))
                pie = base.mark_arc(innerRadius=60, outerRadius=120).encode(
                    color=alt.Color("Participante", scale=color_scale_renda, legend=alt.Legend(orient="bottom", title=None)),
                    order=alt.Order("Renda", sort="descending"),
                    tooltip=[alt.Tooltip("Participante"), alt.Tooltip("Renda", format=",.2f")],
                    opacity=alt.condition(hover_renda, alt.value(1), alt.value(0.7)),
                    stroke=alt.condition(hover_renda, alt.value('white'), alt.value(None)),
                    strokeWidth=alt.condition(hover_renda, alt.value(2), alt.value(0))
                ).add_params(hover_renda)

                st.altair_chart(pie.configure_view(strokeWidth=0), use_container_width=True)
            else:
                st.caption("Renda única ou não informada.")

        # --- SEÇÃO 3: PROJEÇÃO DE FLUXO DE PAGAMENTOS (BAR CHART + ZOOM) ---
        st.markdown("---")
        st.markdown("##### Projeção da Parcela Mensal (Financiamento + Pro Soluto + Atos)")
        
        # Recuperar dados para projeção
        v_fin = d.get('finan_usado', 0)
        p_fin = d.get('prazo_financiamento', 360)
        p_ps = d.get('ps_parcelas', 0)
        v_ps_mensal = d.get('ps_mensal', 0)
        sist = d.get('sistema_amortizacao', 'SAC')
        
        # Recuperar dados de ATOS para o cálculo correto do fluxo inicial
        atos_dict_calc = {
            'ato_final': d.get('ato_final', 0),
            'ato_30': d.get('ato_30', 0),
            'ato_60': d.get('ato_60', 0),
            'ato_90': d.get('ato_90', 0)
        }
        
        if v_fin > 0 and p_fin > 0:
            df_fluxo = calcular_fluxo_pagamento_detalhado(v_fin, p_fin, taxa_fin_vigente(d), sist, v_ps_mensal, p_ps, atos_dict_calc)
            
            # Projeção completa solicitada
            df_view = df_fluxo.copy() 
            
            # CORREÇÃO ALTAIR: Conversão explícita de tipos para evitar SchemaValidationError
            df_view['Mês'] = df_view['Mês'].astype(int)
            df_view['Valor'] = df_view['Valor'].astype(float)
            df_view['Total'] = df_view['Total'].astype(float)
            
            # Definir pontos para as linhas tracejadas
            # 1. Fim dos Atos: Onde termina o último ato (mês 1, 2, 3 ou 4)
            mes_fim_atos = 1
            if d.get('ato_90', 0) > 0: mes_fim_atos = 4
            elif d.get('ato_60', 0) > 0: mes_fim_atos = 3
            elif d.get('ato_30', 0) > 0: mes_fim_atos = 2
            
            # 2. Fim do Pro Soluto: Mês da última parcela
            mes_fim_ps = d.get('ps_parcelas', 0)

            # Cores para cada tipo
            domain_tipo = ['Financiamento', 'Pro Soluto', 'Entrada/Ato']
            range_tipo = [COR_AZUL_ESC, '#f59e0b', COR_VERMELHO] 

            zoom = alt.selection_interval(bind='scales')

            # Base chart with Ordinal x-axis for spacing
            base = alt.Chart(df_view).encode(
                x=alt.X('Mês:O', title='Mês do Financiamento', axis=alt.Axis(labelAngle=0)) # Ordinal para separar
            )

            # Barras Empilhadas
            bars = base.mark_bar().encode(
                y=alt.Y('Valor', title='Valor (R$)', stack='zero'),
                color=alt.Color('Tipo', scale=alt.Scale(domain=domain_tipo, range=range_tipo), legend=alt.Legend(title="Composição")),
                order=alt.Order('Ordem_Tipo', sort='ascending'), # Define a ordem de empilhamento usando a coluna auxiliar
                tooltip=['Mês', 'Tipo', alt.Tooltip('Valor', format=",.2f"), alt.Tooltip('Total', format=",.2f")]
            )

            # Linha Fim Atos
            charts = [bars]
            if mes_fim_atos > 0:
                # Conversão explícita para int e usar mesma coluna 'Mês'
                rule_atos = alt.Chart(pd.DataFrame({'Mês': [int(mes_fim_atos)]})).mark_rule(color='red', strokeDash=[5, 5]).encode(x='Mês:O')
                charts.append(rule_atos)
                
            if mes_fim_ps > 0:
                # Conversão explícita para int e usar mesma coluna 'Mês'
                rule_ps = alt.Chart(pd.DataFrame({'Mês': [int(mes_fim_ps)]})).mark_rule(color='orange', strokeDash=[5, 5]).encode(x='Mês:O')
                charts.append(rule_ps)

            final_chart = alt.layer(*charts).add_params(zoom).properties(height=400)

            st.altair_chart(final_chart, use_container_width=True)
            st.caption("Linha Vermelha Tracejada: Fim dos Atos | Linha Laranja Tracejada: Fim do Pro Soluto")

        # --- SEÇÃO 4: OPORTUNIDADES SEMELHANTES ---
        st.markdown("---")
        st.markdown("##### Oportunidades Semelhantes (Faixa de Preço)")
        
        target_price = d.get('imovel_valor', 0)
        
        try:
            if 'Valor de Venda' in df_estoque.columns and target_price > 0:
                min_p = target_price - 2500
                max_p = target_price + 2500
                
                similares = df_estoque[
                    (df_estoque['Valor de Venda'] >= min_p) & 
                    (df_estoque['Valor de Venda'] <= max_p) &
                    (df_estoque['Empreendimento'] != d.get('empreendimento_nome')) 
                ].sort_values('Valor de Venda').head(10)
                
                if not similares.empty:
                    cards_html = f"""<div class="scrolling-wrapper">"""
                    
                    for idx, row in similares.iterrows():
                         emp_name = row['Empreendimento']
                         unid_name = row['Identificador']
                         val_fmt = fmt_br(row['Valor de Venda'])
                         
                         # Avaliação também
                         aval_fmt = fmt_br(row['Valor de Avaliação Bancária'])
                         
                         cards_html += f"""<div class="card-item">
                            <div class="recommendation-card" style="border-top: 4px solid {COR_AZUL_ESC}; height: 100%; justify-content: flex-start;">
                                <b style="color:{COR_AZUL_ESC}; font-size:1.1rem;">{emp_name}</b><br>
                                <div style="font-size:0.85rem; color:{COR_TEXTO_MUTED}; text-align:center; border-top:1px solid #eee; padding-top:10px; width:100%;"><b>Unidade: {unid_name}</b></div>
                                <div style="margin-top:10px; width:100%;">
                                    <div style="font-size:0.8rem; color:#64748b;">Avaliação</div>
                                    <div style="font-weight:bold; color:{COR_AZUL_ESC};">R$ {aval_fmt}</div>
                                    <div style="font-size:0.8rem; color:#64748b; margin-top:5px;">Venda</div>
                                    <div class="price-tag" style="font-size:1.3rem; margin-top:0;">R$ {val_fmt}</div>
                                </div>
                            </div>
                         </div>"""
                    cards_html += "</div>"
                    st.markdown(cards_html, unsafe_allow_html=True)
                else:
                    st.info("Nenhuma outra unidade encontrada nessa faixa de preço (+/- 2500).")
            else:
                st.info("Dados de estoque indisponíveis para comparação.")
        except Exception:
             st.info("Não foi possível carregar oportunidades semelhantes.")
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        # --- BOTÃO VOLTAR (FULL WIDTH) - estilos em assets/css/streamlit_button_azul.css ---
        st.markdown('<div data-btn-azul style="display:none" aria-hidden="true"></div>', unsafe_allow_html=True)
        if st.button("VOLTAR AO SIMULADOR", use_container_width=True):
             st.session_state.passo_simulacao = 'input'
             scroll_to_top()
             st.rerun()

    # --- ETAPA 1: INPUT ---
    elif passo == 'input':
        st.markdown("### Dados do Cliente")

        # Botão Buscar cliente - largura total da página
        if st.button("BUSCAR CLIENTE (Base Cadastrada)", type="secondary", use_container_width=True, key="btn_home_search"):
            dialog_buscar_cliente(df_cadastros, motor)

        curr_nome = st.session_state.dados_cliente.get('nome', "")
        curr_cpf = st.session_state.dados_cliente.get('cpf', "")
        if curr_cpf:
            curr_cpf = aplicar_mascara_cpf(curr_cpf)
        d_nasc_default = st.session_state.dados_cliente.get('data_nascimento', date(1990, 1, 1))
        if isinstance(d_nasc_default, str):
            try: d_nasc_default = datetime.strptime(d_nasc_default, '%Y-%m-%d').date()
            except:
                try: d_nasc_default = datetime.strptime(d_nasc_default, '%d/%m/%Y').date()
                except: d_nasc_default = date(1990, 1, 1)
        rendas_anteriores = st.session_state.dados_cliente.get('rendas_lista', [])

        st.markdown(f"""<div style="border: 1px solid {COR_BORDA}; border-radius: 12px 12px 0 0; padding: 15px 20px; text-align: center; background: #f8fafc;">
<p style="font-weight: 700; font-size: 1.1rem; margin: 0; color: {COR_AZUL_ESC};">Cadastrar Novo Cliente</p></div>""", unsafe_allow_html=True)
        with st.form("form_cadastro"):
            nome = st.text_input("Nome Completo", value=curr_nome, placeholder="Nome Completo", key="in_nome_v28")
            cpf_val = st.text_input("CPF", value=curr_cpf, placeholder="000.000.000-00", key="in_cpf_v3", max_chars=14)
            data_nasc = st.date_input("Data de Nascimento", value=d_nasc_default, min_value=date(1900, 1, 1), max_value=datetime.now().date(), format="DD/MM/YYYY", key="in_dt_nasc_v3")
            st.markdown("---")
            qtd_part = st.number_input("Participantes na Renda", min_value=1, max_value=4, value=st.session_state.dados_cliente.get('qtd_participantes', 1), step=1, key="qtd_part_v3")
            cols_renda = st.columns(qtd_part)
            lista_rendas_input = []
            def get_val(idx, default):
                v = float(rendas_anteriores[idx]) if idx < len(rendas_anteriores) else default
                return None if v == 0.0 else v
            for i in range(qtd_part):
                with cols_renda[i]:
                    def_val = 3500.0 if i == 0 and not rendas_anteriores else 0.0
                    current_val = get_val(i, def_val)
                    val_display = None if current_val == 0.0 else current_val
                    val_r = st.number_input(f"Renda Part. {i+1}", min_value=0.0, value=val_display, step=100.0, key=f"renda_part_{i}_v3", placeholder="0,00", format="%.2f")
                    lista_rendas_input.append(val_r)
            rank_opts = ["DIAMANTE", "OURO", "PRATA", "BRONZE", "AÇO"]
            curr_ranking = st.session_state.dados_cliente.get('ranking', "DIAMANTE")
            idx_ranking = rank_opts.index(curr_ranking) if curr_ranking in rank_opts else 0
            ranking = st.selectbox("Ranking do Cliente", options=rank_opts, index=idx_ranking, key="in_rank_v28")
            politica_ps = st.selectbox("Política de Pro Soluto", ["Direcional", "Emcash"], index=0 if st.session_state.dados_cliente.get('politica') != "Emcash" else 1, key="in_pol_v28")
            social = st.toggle("Fator Social", value=st.session_state.dados_cliente.get('social', False), key="in_soc_v28")
            cotista = st.toggle("Cotista FGTS", value=st.session_state.dados_cliente.get('cotista', True), key="in_cot_v28")
            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Confirmar e Avançar", type="primary", use_container_width=True)
        st.markdown(f"""<div style="border: 1px solid {COR_BORDA}; border-top: none; border-radius: 0 0 12px 12px; height: 8px; background: #f8fafc;"></div>""", unsafe_allow_html=True)

        if submitted:
            renda_total_calc = sum([r if r is not None else 0.0 for r in lista_rendas_input])
            if not nome.strip(): st.error("Por favor, informe o Nome do Cliente.")
            elif not cpf_val.strip(): st.error("Por favor, informe o CPF do Cliente.")
            else:
                cpf_formatado = aplicar_mascara_cpf(cpf_val)
                if not validar_cpf(cpf_val): st.error("CPF Inválido.")
                elif renda_total_calc <= 0: st.error("A renda total deve ser maior que zero.")
                else:
                    st.session_state.dados_cliente.update({
                        'nome': nome, 'cpf': limpar_cpf_visual(cpf_formatado), 'data_nascimento': data_nasc,
                        'renda': renda_total_calc, 'rendas_lista': [r if r is not None else 0.0 for r in lista_rendas_input],
                        'social': social, 'cotista': cotista, 'ranking': ranking, 'politica': politica_ps,
                        'qtd_participantes': qtd_part, 'finan_usado_historico': 0.0, 'ps_usado_historico': 0.0, 'fgts_usado_historico': 0.0
                    })
                    prazo_ps_max = 66 if politica_ps == "Emcash" else 84
                    f_faixa_ref, s_faixa_ref, _ = motor.obter_enquadramento(renda_total_calc, social, cotista, valor_avaliacao=240000)
                    st.session_state.dados_cliente.update({
                        'prazo_ps_max': prazo_ps_max, 'limit_ps_renda': 0.30,
                        'finan_f_ref': f_faixa_ref, 'sub_f_ref': s_faixa_ref
                    })
                    st.session_state.cliente_ativo = True
                    st.rerun()

        # --- CLIENTE ATIVO (box centralizado) ---
        cliente_ativo = st.session_state.get('cliente_ativo', False)
        nome_cliente = st.session_state.dados_cliente.get('nome', None)
        if cliente_ativo and nome_cliente:
            st.markdown(f"""
            <div style="border: 1px solid {COR_BORDA}; border-radius: 12px; padding: 24px; width: 100%; text-align: center; background: #f8fafc;">
                <p style="font-weight: 700; font-size: 1rem; margin: 0 0 8px 0; color: {COR_AZUL_ESC};">Cliente Ativo</p>
                <p style="font-size: 1.1rem; margin: 0 0 16px 0; color: {COR_VERMELHO}; font-weight: 700;">{nome_cliente}</p>
                <p style="font-size: 0.85rem; color: #64748b; margin: 0;">Selecione como deseja prosseguir com este cliente:</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("PREENCHER VALORES APROVADOS", type="primary", use_container_width=True, key="btn_action_fechamento"):
                st.session_state.passo_simulacao = 'fechamento_aprovado'
                scroll_to_top()
                st.rerun()

    # --- ETAPA 2: VALORES APROVADOS (FECHAMENTO FINANCEIRO) - 2ª ABA ---
    elif passo == 'fechamento_aprovado':
        d = st.session_state.dados_cliente
        st.markdown("### Valores Aprovados (Fechamento Financeiro)")
        st.markdown("<p style='text-align: center; color: #64748b; font-size: 0.9rem;'>Preencha os valores aprovados de financiamento e subsídio. As recomendações usarão esses valores reais.</p>", unsafe_allow_html=True)
        # Recalcular referência da curva (finan_f_ref, sub_f_ref) a partir do perfil do cliente para exibir valores corretos
        renda_cli = float(d.get('renda', 0) or 0)
        social_cli = bool(d.get('social', False))
        cotista_cli = bool(d.get('cotista', True))
        f_curva, s_curva, _ = motor.obter_enquadramento(renda_cli, social_cli, cotista_cli, valor_avaliacao=240000)
        st.session_state.dados_cliente['finan_f_ref'] = f_curva
        st.session_state.dados_cliente['sub_f_ref'] = s_curva
        d = st.session_state.dados_cliente
        if d.get('finan_usado') is None or (isinstance(d.get('finan_usado'), (int, float)) and d.get('finan_usado') == 0):
            st.session_state.dados_cliente['finan_usado'] = d.get('finan_f_ref', 0.0) or 0.0
        if d.get('fgts_sub_usado') is None or (isinstance(d.get('fgts_sub_usado'), (int, float)) and d.get('fgts_sub_usado') == 0):
            st.session_state.dados_cliente['fgts_sub_usado'] = d.get('sub_f_ref', 0.0) or 0.0
        d = st.session_state.dados_cliente
        def _num_f(k, default=0.0):
            v = st.session_state.dados_cliente.get(k, st.session_state.get(k, default))
            if v is None: return default
            try: return float(v)
            except (TypeError, ValueError): return default
        fin_default = _num_f('finan_usado', 0.0)
        f_u = st.number_input("Financiamento Aprovado (R$)", value=st.session_state.get("fin_aprovado_key", fin_default), key="fin_aprovado_key", step=1000.0, format="%.2f", placeholder="0,00")
        if f_u is None: st.session_state['fin_aprovado_key'] = 0.0; f_u = 0.0; st.rerun()
        st.session_state.dados_cliente['finan_usado'] = float(f_u) if f_u is not None else 0.0
        fin_max = d.get("finan_f_ref", 0)
        st.markdown(f'<div class="inline-ref" style="background-color: transparent; padding: 0; font-family: inherit; font-size: 0.72rem; color: {COR_AZUL_ESC}; margin-top: -12px; margin-bottom: 15px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; display: block; opacity: 0.9;">Financiamento Máximo (curva): R$ {fmt_br(fin_max)}</div>', unsafe_allow_html=True)

        sub_default = _num_f('fgts_sub_usado', 0.0)
        s_u = st.number_input("Subsídio Aprovado / FGTS + Subsídio (R$)", value=st.session_state.get("sub_aprovado_key", sub_default), key="sub_aprovado_key", step=1000.0, format="%.2f", placeholder="0,00")
        if s_u is None: st.session_state['sub_aprovado_key'] = 0.0; s_u = 0.0; st.rerun()
        st.session_state.dados_cliente['fgts_sub_usado'] = float(s_u) if s_u is not None else 0.0
        fgts_max = d.get("sub_f_ref", 0)
        st.markdown(f'<div class="inline-ref" style="background-color: transparent; padding: 0; font-family: inherit; font-size: 0.72rem; color: {COR_AZUL_ESC}; margin-top: -12px; margin-bottom: 15px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; display: block; opacity: 0.9;">Subsídio Máximo (curva): R$ {fmt_br(fgts_max)}</div>', unsafe_allow_html=True)

        prazo_atual = d.get('prazo_financiamento', 360)
        try: prazo_atual = int(prazo_atual) if prazo_atual is not None else 360
        except: prazo_atual = 360
        prazo_sel = st.number_input("Prazo do Financiamento (meses)", value=st.session_state.get("prazo_aprovado_key", prazo_atual), key="prazo_aprovado_key", min_value=12, max_value=600, step=1)
        if prazo_sel is None: st.session_state['prazo_aprovado_key'] = 360; prazo_sel = 360; st.rerun()
        st.session_state.dados_cliente['prazo_financiamento'] = int(prazo_sel)

        idx_tab = 0 if d.get('sistema_amortizacao', "SAC") == "SAC" else 1
        sist_sel = st.selectbox("Sistema de Amortização", ["SAC", "PRICE"], index=idx_tab, key="sist_aprovado_key")
        st.session_state.dados_cliente['sistema_amortizacao'] = sist_sel
        taxa_padrao = taxa_fin_vigente(d)
        sac_details = calcular_comparativo_sac_price(f_u, int(prazo_sel), taxa_padrao)["SAC"]
        price_details = calcular_comparativo_sac_price(f_u, int(prazo_sel), taxa_padrao)["PRICE"]
        st.markdown(f"""<div style="margin-top: -8px; margin-bottom: 15px; font-size: 0.85rem; color: #64748b;"><b>SAC:</b> R$ {fmt_br(sac_details['primeira'])} a R$ {fmt_br(sac_details['ultima'])} (Juros totais: R$ {fmt_br(sac_details['juros'])}) &nbsp;|&nbsp; <b>PRICE:</b> R$ {fmt_br(price_details['parcela'])} fixas (Juros totais: R$ {fmt_br(price_details['juros'])})</div>""", unsafe_allow_html=True)

        st.markdown("---")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            if st.button("Avançar para Recomendação de Imóveis", type="primary", use_container_width=True, key="btn_fech_to_guide"):
                st.session_state.passo_simulacao = 'guide'; scroll_to_top(); st.rerun()
        with col_f2:
            if st.button("Escolha direta de unidade (estoque)", use_container_width=True, key="btn_fech_to_selection"):
                st.session_state.passo_simulacao = 'selection'; scroll_to_top(); st.rerun()
        st.markdown('<div data-btn-azul style="display:none" aria-hidden="true"></div>', unsafe_allow_html=True)
        if st.button("Voltar para Dados do Cliente", use_container_width=True, key="btn_fech_voltar"): st.session_state.passo_simulacao = 'input'; scroll_to_top(); st.rerun()

    # --- ETAPA 3: RECOMENDAÇÃO (usa valores reais do fechamento) ---
    elif passo == 'guide':
        d = st.session_state.dados_cliente
        st.markdown("### Recomendação de Imóveis")

        df_disp_total = df_estoque.copy()

        if df_disp_total.empty: st.markdown('<div class="custom-alert">Sem produtos viaveis no perfil selecionado.</div>', unsafe_allow_html=True); df_viaveis = pd.DataFrame()
        else:
            def calcular_viabilidade_unidade(row):
                v_venda = row['Valor de Venda']
                v_aval = row['Valor de Avaliação Bancária']
                try: v_venda = float(v_venda)
                except: v_venda = 0.0
                try: v_aval = float(v_aval)
                except: v_aval = v_venda
                # Usar valores reais do fechamento (2ª aba), não da curva
                fin = float(d.get('finan_usado', 0) or 0)
                sub = float(d.get('fgts_sub_usado', 0) or 0)
                # SELEÇÃO DO PRO SOLUTO POR COLUNA
                pol = d.get('politica', 'Direcional')
                rank = d.get('ranking', 'DIAMANTE')
                ps_max_val = 0.0
                if pol == 'Emcash':
                    ps_max_val = row.get('PS_EmCash', 0.0)
                else:
                    col_rank = f"PS_{rank.title()}" if rank else 'PS_Diamante'
                    if rank == 'AÇO': col_rank = 'PS_Aco'
                    ps_max_val = row.get(col_rank, 0.0)
                capacity = ps_max_val + fin + sub + (2 * d.get('renda', 0))
                cobertura = (capacity / v_venda) * 100 if v_venda > 0 else 0
                is_viavel = capacity >= v_venda
                return pd.Series([capacity, cobertura, is_viavel, fin, sub])

            df_disp_total[['Poder_Compra', 'Cobertura', 'Viavel', 'Finan_Unid', 'Sub_Unid']] = df_disp_total.apply(calcular_viabilidade_unidade, axis=1)
            df_viaveis = df_disp_total[df_disp_total['Viavel']].copy()

        tab_viaveis, tab_sugestoes, tab_estoque = st.tabs(["EMPREENDIMENTOS VIÁVEIS", "RECOMENDAÇÃO DE UNIDADES", "ESTOQUE GERAL"])

        with tab_viaveis:
             st.markdown("<br>", unsafe_allow_html=True)
             if df_viaveis.empty:
                 if not df_disp_total.empty:
                    cheapest = df_disp_total.sort_values('Valor de Venda', ascending=True).iloc[0]
                    emp_fallback = cheapest['Empreendimento']
                    st.markdown(f"""
                                <div class="card" style="min-height: 80px; padding: 15px; border-top: 3px solid {COR_AZUL_ESC};">
                                    <p style="margin:0; font-weight:700; color:{COR_AZUL_ESC};">{emp_fallback}</p>
                                    <p style="margin:5px 0 0 0; font-size:0.85rem; color:{COR_TEXTO_MUTED};">Melhor preço disponível: R$ {fmt_br(cheapest['Valor de Venda'])}</p>
                                </div>
                        """, unsafe_allow_html=True)
                 else:
                    st.error("Sem estoque disponível.")
             else:
                emp_counts = df_viaveis.groupby('Empreendimento').size().to_dict()
                items = list(emp_counts.items())
                cols_per_row = 3
                for i in range(0, len(items), cols_per_row):
                    row_items = items[i:i+cols_per_row]
                    row_cols = st.columns(len(row_items))
                    for idx, (emp, qtd) in enumerate(row_items):
                        with row_cols[idx]:
                            st.markdown(f"""
                                <div class="card" style="min-height: 80px; padding: 15px; border-top: 3px solid {COR_AZUL_ESC};">
                                    <p style="margin:0; font-weight:700; color:{COR_AZUL_ESC};">{emp}</p>
                                    <p style="margin:5px 0 0 0; font-size:0.85rem; color:{COR_TEXTO_MUTED};">{qtd} unidades viáveis</p>
                                </div>
                            """, unsafe_allow_html=True)

        with tab_sugestoes:
            st.markdown("<br>", unsafe_allow_html=True)
            emp_names_rec = sorted(df_disp_total['Empreendimento'].unique().tolist())
            emp_rec = st.selectbox("Escolha um empreendimento para obter recomendações:", options=["Todos"] + emp_names_rec, key="sel_emp_rec_v28")
            df_pool = df_disp_total if emp_rec == "Todos" else df_disp_total[df_disp_total['Empreendimento'] == emp_rec]

            if df_pool.empty: st.markdown('<div class="custom-alert">Nenhuma unidade encontrada.</div>', unsafe_allow_html=True)
            else:
                pool_viavel = df_pool[df_pool['Viavel']]
                cand_facil = pd.DataFrame(); cand_ideal = pd.DataFrame(); cand_seguro = pd.DataFrame()
                
                final_cards = []

                if not pool_viavel.empty:
                    min_price_vi = pool_viavel['Valor de Venda'].min()
                    cand_facil = pool_viavel[pool_viavel['Valor de Venda'] == min_price_vi]
                    
                    max_cob = pool_viavel['Cobertura'].max()
                    cand_seguro = pool_viavel[pool_viavel['Cobertura'] == max_cob]
                    
                    ideal_pool = pool_viavel[pool_viavel['Cobertura'] >= 100]
                    if not ideal_pool.empty:
                        max_price_ideal = ideal_pool['Valor de Venda'].max()
                        cand_ideal = ideal_pool[ideal_pool['Valor de Venda'] == max_price_ideal]
                    else:
                        max_price_ideal = pool_viavel['Valor de Venda'].max()
                        cand_ideal = pool_viavel[pool_viavel['Valor de Venda'] == max_price_ideal]
                else:
                      fallback_pool = df_pool.sort_values('Valor de Venda', ascending=True)
                      if not fallback_pool.empty:
                          min_p = fallback_pool['Valor de Venda'].min()
                          cand_facil = fallback_pool[fallback_pool['Valor de Venda'] == min_p].head(5)
                          max_p = fallback_pool['Valor de Venda'].max()
                          cand_ideal = fallback_pool[fallback_pool['Valor de Venda'] == max_p].head(5)
                          cand_seguro = fallback_pool.iloc[[len(fallback_pool)//2]]

                def add_cards_group(label, df_group, css_class):
                    df_u = df_group.drop_duplicates(subset=['Identificador'])
                    for _, row in df_u.head(6).iterrows():
                        final_cards.append({'label': label, 'row': row, 'css': css_class})

                add_cards_group('IDEAL', cand_ideal, 'badge-ideal')
                add_cards_group('SEGURO', cand_seguro, 'badge-seguro')
                add_cards_group('FACILITADO', cand_facil, 'badge-facilitado')

                if not final_cards: st.warning("Nenhuma unidade encontrada.")
                else:
                    cards_html = f"""<div class="scrolling-wrapper">"""
                    
                    for card in final_cards:
                         row = card['row']
                         emp_name = row['Empreendimento']
                         unid_name = row['Identificador']
                         val_fmt = fmt_br(row['Valor de Venda'])
                         aval_fmt = fmt_br(row['Valor de Avaliação Bancária'])
                         label = card['label']
                         css_badge = card['css']
                         
                         cards_html += f"""
                         <div class="card-item">
                            <div class="recommendation-card" style="border-top: 4px solid {COR_AZUL_ESC}; height: 100%; justify-content: flex-start;">
                                <span style="font-size:0.65rem; color:{COR_AZUL_ESC}; opacity:0.8;">PERFIL</span><br>
                                <div style="margin-top:5px; margin-bottom:15px;"><span class="{css_badge}">{label}</span></div>
                                <b style="color:{COR_AZUL_ESC}; font-size:1.1rem;">{emp_name}</b><br>
                                <div style="font-size:0.85rem; color:{COR_TEXTO_MUTED}; text-align:center; border-top:1px solid #eee; padding-top:10px; width:100%;">
                                    <b>Unidade: {unid_name}</b>
                                </div>
                                <div style="margin: 10px 0; width: 100%;">
                                    <div style="font-size:0.8rem; color:#64748b;">Avaliação</div>
                                    <div style="font-weight:bold; color:{COR_AZUL_ESC};">R$ {aval_fmt}</div>
                                    <div style="font-size:0.8rem; color:#64748b; margin-top:5px;">Venda</div>
                                    <div class="price-tag" style="font-size:1.3rem; margin-top:0;">R$ {val_fmt}</div>
                                </div>
                            </div>
                         </div>"""
                    cards_html += "</div>"
                    st.markdown(cards_html, unsafe_allow_html=True)

        with tab_estoque:
             if df_disp_total.empty:
                st.markdown('<div class="custom-alert">Sem dados para exibir.</div>', unsafe_allow_html=True)
             else:
                f_cols = st.columns([1.2, 1.5, 1, 1, 1])
                with f_cols[0]: f_bairro = st.multiselect("Bairro:", options=sorted(df_disp_total['Bairro'].unique()), key="f_bairro_tab_v28")
                with f_cols[1]: f_emp = st.multiselect("Empreendimento:", options=sorted(df_disp_total['Empreendimento'].unique()), key="f_emp_tab_v28")
                with f_cols[2]:
                    cob_opts = ["Todas", "Acima de 10%", "Acima de 20%", "Acima de 30%", "Acima de 40%", "Acima de 50%", "Acima de 60%", "Acima de 70%", "Acima de 80%", "Acima de 90%", "100%"]
                    f_cob_sel = st.selectbox("Cobertura Mínima:", options=cob_opts, key="f_cob_sel_v28")
                    cob_min_val = 0
                    if "10%" in f_cob_sel: cob_min_val = 10
                    elif "20%" in f_cob_sel: cob_min_val = 20
                    elif "30%" in f_cob_sel: cob_min_val = 30
                    elif "40%" in f_cob_sel: cob_min_val = 40
                    elif "50%" in f_cob_sel: cob_min_val = 50
                    elif "60%" in f_cob_sel: cob_min_val = 60
                    elif "70%" in f_cob_sel: cob_min_val = 70
                    elif "80%" in f_cob_sel: cob_min_val = 80
                    elif "90%" in f_cob_sel: cob_min_val = 90
                    elif "100%" in f_cob_sel: cob_min_val = 100

                with f_cols[3]: f_ordem = st.selectbox("Ordem:", ["Menor Preço", "Maior Preço"], key="f_ordem_tab_v28")
                with f_cols[4]: f_pmax = st.number_input("Preço Máx:", value=None, key="f_pmax_tab_v28", placeholder="0,00")

                df_tab = df_disp_total.copy()
                if f_bairro: df_tab = df_tab[df_tab['Bairro'].isin(f_bairro)]
                if f_emp: df_tab = df_tab[df_tab['Empreendimento'].isin(f_emp)]
                df_tab = df_tab[df_tab['Cobertura'] >= cob_min_val]
                if f_pmax: df_tab = df_tab[df_tab['Valor de Venda'] <= f_pmax]

                if f_ordem == "Menor Preço": df_tab = df_tab.sort_values('Valor de Venda', ascending=True)
                else: df_tab = df_tab.sort_values('Valor de Venda', ascending=False)

                df_tab_view = df_tab.copy()
                df_tab_view['Valor de Venda'] = df_tab_view['Valor de Venda'].apply(fmt_br)
                df_tab_view['Valor de Avaliação Bancária'] = df_tab_view['Valor de Avaliação Bancária'].apply(fmt_br)
                df_tab_view['Poder_Compra'] = df_tab_view['Poder_Compra'].apply(fmt_br)
                df_tab_view['Cobertura'] = df_tab_view['Cobertura'].apply(lambda x: f"{x:.1f}%")

                st.dataframe(
                    df_tab_view[['Identificador', 'Bairro', 'Empreendimento', 'Valor de Avaliação Bancária', 'Valor de Venda', 'Poder_Compra', 'Cobertura']],
                    use_container_width=True, hide_index=True,
                    column_config={
                        "Identificador": st.column_config.TextColumn("Unidade"),
                        "Valor de Avaliação Bancária": st.column_config.TextColumn("Avaliação (R$)"),
                        "Valor de Venda": st.column_config.TextColumn("Venda (R$)"),
                        "Poder_Compra": st.column_config.TextColumn("Poder Real (R$)"),
                        "Cobertura": st.column_config.TextColumn("Cobertura"),
                    }
                )

        st.markdown("---")
        if st.button("Avançar para Escolha de Unidade", type="primary", use_container_width=True, key="btn_goto_selection"): st.session_state.passo_simulacao = 'selection'; scroll_to_top(); st.rerun()
        st.write("");
        st.markdown('<div data-btn-azul style="display:none" aria-hidden="true"></div>', unsafe_allow_html=True)
        if st.button("Voltar para Valores Aprovados", use_container_width=True, key="btn_pot_v28"): st.session_state.passo_simulacao = 'fechamento_aprovado'; scroll_to_top(); st.rerun()

    elif passo == 'selection':
         d = st.session_state.dados_cliente
         st.markdown("### Escolha de Unidade")
         
         df_disponiveis = df_estoque.copy()
         if df_disponiveis.empty: st.warning("Sem estoque disponível.")
         else:
            emp_names = sorted(df_disponiveis['Empreendimento'].unique())
            idx_emp = 0
            if 'empreendimento_nome' in st.session_state.dados_cliente:
                try: idx_emp = emp_names.index(st.session_state.dados_cliente['empreendimento_nome'])
                except: idx_emp = 0
            emp_escolhido = st.selectbox("Escolha o Empreendimento:", options=emp_names, index=idx_emp, key="sel_emp_new_v3")
            st.session_state.dados_cliente['empreendimento_nome'] = emp_escolhido
            unidades_disp = df_disponiveis[(df_disponiveis['Empreendimento'] == emp_escolhido)].copy()
            unidades_disp = unidades_disp.sort_values(['Bloco_Sort', 'Andar', 'Apto_Sort'])
            if unidades_disp.empty: st.warning("Sem unidades disponíveis.")
            else:
                current_uni_ids = unidades_disp['Identificador'].unique(); idx_uni = 0
                if 'unidade_id' in st.session_state.dados_cliente:
                    try:
                        idx_list = list(current_uni_ids)
                        if st.session_state.dados_cliente['unidade_id'] in idx_list: idx_uni = idx_list.index(st.session_state.dados_cliente['unidade_id'])
                    except: pass
                def label_uni(uid):
                    u = unidades_disp[unidades_disp['Identificador'] == uid].iloc[0]
                    v_aval = fmt_br(u['Valor de Avaliação Bancária'])
                    v_venda = fmt_br(u['Valor de Venda'])
                    return f"{uid} | Aval: R$ {v_aval} | Venda: R$ {v_venda}"
                
                uni_escolhida_id = st.selectbox("Escolha a Unidade:", options=current_uni_ids, index=idx_uni, format_func=label_uni, key="sel_uni_new_v3")
                st.session_state.dados_cliente['unidade_id'] = uni_escolhida_id
                if uni_escolhida_id:
                    u_row = unidades_disp[unidades_disp['Identificador'] == uni_escolhida_id].iloc[0]
                    v_aval = u_row['Valor de Avaliação Bancária']; v_venda = u_row['Valor de Venda']
                    # Usar valores reais do fechamento (2ª aba)
                    fin_t = float(d.get('finan_usado', 0) or 0)
                    sub_t = float(d.get('fgts_sub_usado', 0) or 0)
                    # SELEÇÃO DO PRO SOLUTO POR COLUNA
                    pol = d.get('politica', 'Direcional')
                    rank = d.get('ranking', 'DIAMANTE')
                    
                    ps_max_val = 0.0
                    if pol == 'Emcash':
                        ps_max_val = u_row.get('PS_EmCash', 0.0)
                    else:
                        col_rank = f"PS_{rank.title()}" if rank else 'PS_Diamante'
                        if rank == 'AÇO': col_rank = 'PS_Aco'
                        ps_max_val = u_row.get(col_rank, 0.0)

                    # Definir limite de parcelas
                    prazo_max_ps = 66 if pol == 'Emcash' else 84
                    st.session_state.dados_cliente['prazo_ps_max'] = prazo_max_ps

                    poder_t, _ = motor.calcular_poder_compra(d.get('renda', 0), fin_t, sub_t, ps_max_val)
                    # Termômetro usa valor final de venda (se preenchido), senão valor da unidade
                    valor_para_termo = st.session_state.get('valor_final_unidade_key')
                    if valor_para_termo is None or (isinstance(valor_para_termo, (int, float)) and valor_para_termo <= 0):
                        valor_para_termo = float(v_venda)
                    else:
                        valor_para_termo = float(valor_para_termo)
                    percentual_cobertura = min(100, max(0, (poder_t / valor_para_termo) * 100)) if valor_para_termo > 0 else 0
                    cor_term = calcular_cor_gradiente(percentual_cobertura)
                    st.markdown(f"""
                        <div style="margin-top: 20px; padding: 15px; border: 1px solid #e2e8f0; border-radius: 10px; background-color: #f8fafc; text-align: center;">
                            <div style="display: flex; justify-content: space-around; margin-bottom: 10px; font-size: 0.9rem;">
                                <div><b>Valor de Avaliação:</b><br>R$ {fmt_br(v_aval)}</div>
                                <div><b>Valor considerado (Venda):</b><br>R$ {fmt_br(valor_para_termo)}</div>
                            </div>
                            <hr style="margin: 10px 0; border: 0; border-top: 1px solid #e2e8f0;">
                            <p style="margin: 0; font-weight: 700; font-size: 0.9rem; color: #002c5d;">TERMÔMETRO DE VIABILIDADE</p>
                            <div style="width: 100%; background-color: #e2e8f0; border-radius: 5px; height: 10px; margin: 10px 0;">
                                <div style="width: {percentual_cobertura}%; background: linear-gradient(90deg, #e30613 0%, #002c5d 100%); height: 100%; border-radius: 5px; transition: width 0.5s;"></div>
                            </div>
                            <small>{percentual_cobertura:.1f}% Coberto</small>
                        </div>
                    """, unsafe_allow_html=True)
                    # Campo Valor Final da Unidade (desconto/alteração) na aba de escolha
                    st.markdown("#### Valor Final da Unidade")
                    v_final_default = float(u_row['Valor de Venda'])
                    if d.get('imovel_valor') and d.get('unidade_id') == uni_escolhida_id:
                        v_final_default = float(d.get('imovel_valor'))
                    st.number_input("Valor Final de Venda (R$)", value=v_final_default, key="valor_final_unidade_key", step=1000.0, format="%.2f", placeholder="Igual ao valor da unidade se não alterar")
                    st.caption("Opcional: preencha se houver desconto ou valor diferente do cadastro. O fechamento será calculado com base neste valor.")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Avançar para Fechamento Financeiro", type="primary", use_container_width=True):
                if uni_escolhida_id:
                    u_row = unidades_disp[unidades_disp['Identificador'] == uni_escolhida_id].iloc[0]
                    v_venda_unid = float(u_row['Valor de Venda'])
                    valor_final = st.session_state.get('valor_final_unidade_key')
                    if valor_final is not None and valor_final > 0:
                        imovel_valor_usar = float(valor_final)
                    else:
                        imovel_valor_usar = v_venda_unid
                    st.session_state.dados_cliente.update({
                        'unidade_id': uni_escolhida_id, 'empreendimento_nome': emp_escolhido,
                        'imovel_valor': imovel_valor_usar, 'imovel_avaliacao': u_row['Valor de Avaliação Bancária'],
                        'finan_estimado': d.get('finan_usado', 0), 'fgts_sub': d.get('fgts_sub_usado', 0),
                        'unid_entrega': u_row.get('Data Entrega', ''),
                        'unid_area': u_row.get('Area', ''),
                        'unid_tipo': u_row.get('Tipologia', ''),
                        'unid_endereco': u_row.get('Endereco', ''),
                        'unid_bairro': u_row.get('Bairro', ''),
                        'volta_caixa_ref': u_row.get('Volta_Caixa_Ref', 0.0)
                    })
                    st.session_state.passo_simulacao = 'payment_flow'; scroll_to_top(); st.rerun()
            st.markdown('<div data-btn-azul style="display:none" aria-hidden="true"></div>', unsafe_allow_html=True)
            if st.button("Voltar para Recomendação de Imóveis", use_container_width=True): st.session_state.passo_simulacao = 'guide'; scroll_to_top(); st.rerun()

    elif passo == 'payment_flow':
        d = st.session_state.dados_cliente
        st.markdown("### Distribuição da Entrada (Fechamento)")
        # Valores já preenchidos na 2ª aba (Fechamento) e na escolha da unidade (garantir numérico)
        u_valor = float(d.get('imovel_valor', 0) or 0)
        u_nome = d.get('empreendimento_nome', 'N/A')
        u_unid = d.get('unidade_id', 'N/A')
        u_aval = d.get('imovel_avaliacao', u_valor)
        f_u_input = float(d.get('finan_usado', 0) or 0)
        fgts_u_input = float(d.get('fgts_sub_usado', 0) or 0)
        prazo_finan = int(d.get('prazo_financiamento', 360))
        tab_fin = d.get('sistema_amortizacao', 'SAC')
        st.session_state.dados_cliente['finan_usado'] = f_u_input
        st.session_state.dados_cliente['fgts_sub_usado'] = fgts_u_input
        st.session_state.dados_cliente['prazo_financiamento'] = prazo_finan
        st.session_state.dados_cliente['sistema_amortizacao'] = tab_fin

        st.markdown(f"""
        <div class="custom-alert" style="flex-direction: column; align-items: center; text-align: center; padding: 20px;">
            <div style="font-size: 1.1rem; margin-bottom: 5px;">{u_nome} - {u_unid}</div>
            <div style="font-size: 0.9rem; opacity: 0.9;">Valor Final da Unidade: <b>R$ {fmt_br(u_valor)}</b></div>
            <div style="font-size: 0.9rem; opacity: 0.9;">Financiamento: R$ {fmt_br(f_u_input)} | Subsídio: R$ {fmt_br(fgts_u_input)} | Prazo: {prazo_finan}x | {tab_fin}</div>
        </div>
        """, unsafe_allow_html=True)

        if 'ps_usado' not in st.session_state.dados_cliente: st.session_state.dados_cliente['ps_usado'] = 0.0
        if 'ato_final' not in st.session_state.dados_cliente: st.session_state.dados_cliente['ato_final'] = 0.0
        if 'ato_30' not in st.session_state.dados_cliente: st.session_state.dados_cliente['ato_30'] = 0.0
        if 'ato_60' not in st.session_state.dados_cliente: st.session_state.dados_cliente['ato_60'] = 0.0
        if 'ato_90' not in st.session_state.dados_cliente: st.session_state.dados_cliente['ato_90'] = 0.0
        def _num_val(k, default=0.0):
            v = st.session_state.get(k, default)
            if v is None: return default
            try: return float(v)
            except (TypeError, ValueError): return default

        st.markdown("#### Distribuição da Entrada (Saldo a Pagar)")
        
        if 'ps_u_key' not in st.session_state:
             st.session_state['ps_u_key'] = st.session_state.dados_cliente.get('ps_usado', 0.0)
        ps_atual = _num_val('ps_u_key', 0.0)
        
        # Saldo para atos = Valor - Finan - FGTS - PS
        saldo_para_atos = max(0.0, u_valor - f_u_input - fgts_u_input - ps_atual)
        
        # Inicializa chaves de atos se necessário
        if 'ato_1_key' not in st.session_state: st.session_state['ato_1_key'] = st.session_state.dados_cliente.get('ato_final', 0.0)
        if 'ato_2_key' not in st.session_state: st.session_state['ato_2_key'] = st.session_state.dados_cliente.get('ato_30', 0.0)
        if 'ato_3_key' not in st.session_state: st.session_state['ato_3_key'] = st.session_state.dados_cliente.get('ato_60', 0.0)
        if 'ato_4_key' not in st.session_state: st.session_state['ato_4_key'] = st.session_state.dados_cliente.get('ato_90', 0.0)
        
        is_emcash = (d.get('politica') == 'Emcash')
        
        # --- Ato 1 (Imediato): campo vazio → 0 ao sair do campo ---
        v1 = _num_val('ato_1_key', 0.0)
        r1 = st.number_input("Ato (Entrada Imediata)", value=st.session_state.get("ato_1_key", v1), key="ato_1_key", min_value=0.0, step=100.0, format="%.2f", placeholder="0,00", help="Valor pago no ato da assinatura.")
        if r1 is None: st.session_state['ato_1_key'] = 0.0; st.rerun()
        st.session_state.dados_cliente['ato_final'] = float(r1) if r1 is not None else 0.0
        
        # Função para distribuir o restante (usa PS atual da session)
        def distribuir_restante(n_parcelas):
            a1_atual = float(st.session_state.get('ato_1_key') or 0.0)
            ps_atual_cb = float(st.session_state.get('ps_u_key') or 0.0)
            gap_total = max(0.0, u_valor - f_u_input - fgts_u_input - ps_atual_cb)
            
            # Restante a distribuir nos outros atos
            restante = max(0.0, gap_total - a1_atual)
            
            if restante > 0 and n_parcelas > 0:
                val_per_target = restante / n_parcelas
                
                # Distribuir conforme politica
                if n_parcelas == 2: # 30/60
                    st.session_state['ato_2_key'] = val_per_target
                    st.session_state['ato_3_key'] = val_per_target
                    st.session_state['ato_4_key'] = 0.0
                elif n_parcelas == 3: # 30/60/90
                    st.session_state['ato_2_key'] = val_per_target
                    st.session_state['ato_3_key'] = val_per_target
                    st.session_state['ato_4_key'] = val_per_target
            else:
                # Se não há restante ou negativo, zerar futuros
                st.session_state['ato_2_key'] = 0.0
                st.session_state['ato_3_key'] = 0.0
                st.session_state['ato_4_key'] = 0.0

            # Atualizar session persistente
            st.session_state.dados_cliente['ato_30'] = st.session_state['ato_2_key']
            st.session_state.dados_cliente['ato_60'] = st.session_state['ato_3_key']
            st.session_state.dados_cliente['ato_90'] = st.session_state['ato_4_key']

        st.markdown('<label style="font-size: 0.8rem; font-weight: 600;">Opções de Redistribuição do Saldo Restante:</label>', unsafe_allow_html=True)
        col_dist_a, col_dist_b = st.columns(2)
        
        # Botões de distribuição do restante
        with col_dist_a: 
            st.button("Distribuir Restante em 2x (30/60)", use_container_width=True, key="btn_rest_2x", on_click=distribuir_restante, args=(2,))
        with col_dist_b: 
            st.button("Distribuir Restante em 3x (30/60/90)", use_container_width=True, disabled=is_emcash, key="btn_rest_3x", on_click=distribuir_restante, args=(3,))
        
        st.write("") 
        col_atos_rest1, col_atos_rest2, col_atos_rest3 = st.columns(3)
        
        with col_atos_rest1:
            r2 = st.number_input("Ato 30 Dias", value=st.session_state.get("ato_2_key", _num_val('ato_2_key', 0.0)), key="ato_2_key", min_value=0.0, step=100.0, format="%.2f", placeholder="0,00")
            if r2 is None: st.session_state['ato_2_key'] = 0.0; st.rerun()
            st.session_state.dados_cliente['ato_30'] = float(r2) if r2 is not None else 0.0
            
        with col_atos_rest2:
            r3 = st.number_input("Ato 60 Dias", value=st.session_state.get("ato_3_key", _num_val('ato_3_key', 0.0)), key="ato_3_key", min_value=0.0, step=100.0, format="%.2f", placeholder="0,00")
            if r3 is None: st.session_state['ato_3_key'] = 0.0; st.rerun()
            st.session_state.dados_cliente['ato_60'] = float(r3) if r3 is not None else 0.0
            
        with col_atos_rest3:
            r4 = st.number_input("Ato 90 Dias", value=st.session_state.get("ato_4_key", _num_val('ato_4_key', 0.0)), key="ato_4_key", min_value=0.0, step=100.0, disabled=is_emcash, format="%.2f", placeholder="0,00")
            if r4 is None: st.session_state['ato_4_key'] = 0.0; st.rerun()
            st.session_state.dados_cliente['ato_90'] = float(r4) if r4 is not None else 0.0
            
        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
        col_ps_val, col_ps_parc = st.columns(2)
        
        # Recuperação do limite de Pro Soluto via coluna da tabela estoque
        ps_max_real = 0.0
        if 'unidade_id' in d and 'empreendimento_nome' in d:
             # Filtra na tabela estoque
             # Note: df_estoque está disponível no escopo de aba_simulador_automacao
             row_u = df_estoque[(df_estoque['Identificador'] == d['unidade_id']) & (df_estoque['Empreendimento'] == d['empreendimento_nome'])]
             if not row_u.empty:
                 row_u = row_u.iloc[0]
                 pol = d.get('politica', 'Direcional')
                 rank = d.get('ranking', 'DIAMANTE')
                 if pol == 'Emcash':
                     ps_max_real = row_u.get('PS_EmCash', 0.0)
                 else:
                     col_rank = f"PS_{rank.title()}" if rank else 'PS_Diamante'
                     if rank == 'AÇO': col_rank = 'PS_Aco'
                     ps_max_real = row_u.get(col_rank, 0.0)

        # Motor Pro Soluto (COMPARADOR + POLITICAS) — limites e parcela corrigida (não é PS/N)
        try:
            mps = metricas_pro_soluto(
                renda=float(d.get("renda", 0) or 0),
                valor_unidade=u_valor,
                politica_ui=str(d.get("politica", "Direcional")),
                ranking=str(d.get("ranking", "DIAMANTE")),
                premissas=_prem,
                df_politicas=df_politicas,
                ps_cap_estoque=float(ps_max_real) if ps_max_real else None,
            )
        except Exception:
            mps = {
                "parcela_max_j8": 0.0,
                "parcela_max_g14": 0.0,
                "ps_max_efetivo": float(ps_max_real or 0),
                "ps_max_comparador_politica": 0.0,
                "cap_valor_unidade": 0.0,
                "prazo_ps_politica": int(d.get("prazo_ps_max", 60) or 60),
            }
        ps_limite_ui = float(mps.get("ps_max_efetivo", 0) or 0)
        prazo_cap_app = int(d.get("prazo_ps_max", 84) or 84)
        pol_prazo = int(mps.get("prazo_ps_politica", prazo_cap_app) or prazo_cap_app)
        parc_max_ui = max(1, min(pol_prazo, prazo_cap_app))

        with col_ps_val:
            ps_input_val = st.number_input("Pro Soluto Direcional", value=st.session_state.get("ps_u_key", _num_val('ps_u_key', 0.0)), key="ps_u_key", step=1000.0, format="%.2f", placeholder="0,00")
            if ps_input_val is None: st.session_state['ps_u_key'] = 0.0; ps_input_val = 0.0; st.rerun()
            st.session_state.dados_cliente['ps_usado'] = float(ps_input_val) if ps_input_val is not None else 0.0
            ref_text_ps = f"Limite máximo de Pro Soluto: R$ {fmt_br(ps_limite_ui)}"
            st.markdown(f'<div class="inline-ref" style="background-color: transparent; padding: 0; font-family: inherit; font-size: 0.72rem; color: {COR_AZUL_ESC}; margin-top: -12px; margin-bottom: 15px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; display: block; opacity: 0.9;">{ref_text_ps}</div>', unsafe_allow_html=True)
            st.caption(
                f"Parcela máxima (simulador Excel, C43/G14 — λ tier − 30% × renda): "
                f"R$ {fmt_br(mps.get('parcela_max_g14', 0))}"
            )
            
        with col_ps_parc:
            if 'parc_ps_key' not in st.session_state: st.session_state['parc_ps_key'] = d.get('ps_parcelas', min(60, parc_max_ui))
            parc_val = st.number_input("Parcelas Pro Soluto", min_value=1, max_value=parc_max_ui, key="parc_ps_key")
            parc = int(parc_val) if parc_val is not None and parc_val >= 1 else 1
            st.session_state.dados_cliente['ps_parcelas'] = parc
            st.markdown(f'<span class="inline-ref">Prazo máx. parcelas: {parc_max_ui} meses (política {pol_prazo} × app {prazo_cap_app})</span>', unsafe_allow_html=True)
        
        v_parc = parcela_ps_para_valor(
            float(ps_input_val or 0),
            parc,
            str(d.get("politica", "Direcional")),
            _prem,
        )
        st.session_state.dados_cliente['ps_mensal'] = v_parc
        st.session_state.dados_cliente['ps_mensal_simples'] = (float(ps_input_val or 0) / parc) if parc > 0 else 0.0
        st.markdown(f'<div style="margin-top: -8px; margin-bottom: 15px; font-size: 0.9rem; font-weight: 600; color: {COR_AZUL_ESC}; text-align: center;">Mensalidade PS (PMT×(1+E1)): R$ {fmt_br(v_parc)} ({parc}x)</div>', unsafe_allow_html=True)
        st.caption("A mensalidade usa taxa e encargos do comparador (I5), não apenas valor do PS ÷ parcelas.")
        
        # --- INPUT VOLTA AO CAIXA (NOVO) ---
        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
        if 'volta_caixa_key' not in st.session_state: st.session_state['volta_caixa_key'] = 0.0
        
        vc_ref = d.get('volta_caixa_ref', 0.0)
        vc_input_val = st.number_input("Volta ao Caixa", value=st.session_state.get("volta_caixa_key", _num_val('volta_caixa_key', 0.0)), key="volta_caixa_key", step=1000.0, format="%.2f", placeholder="0,00")
        if vc_input_val is None: st.session_state['volta_caixa_key'] = 0.0; vc_input_val = 0.0; st.rerun()
        vc_input_val = float(vc_input_val) if vc_input_val is not None else 0.0
        
        ref_text_vc = f"Folga Volta ao Caixa: R$ {fmt_br(vc_ref)}"
        st.markdown(f'<div class="inline-ref" style="background-color: transparent; padding: 0; font-family: inherit; font-size: 0.72rem; color: {COR_AZUL_ESC}; margin-top: -12px; margin-bottom: 15px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; display: block; opacity: 0.9;">{ref_text_vc}</div>', unsafe_allow_html=True)
        
        # Recalcular valores atuais para o resumo
        r1_val = st.session_state.dados_cliente['ato_final']
        r2_val = st.session_state.dados_cliente['ato_30']
        r3_val = st.session_state.dados_cliente['ato_60']
        r4_val = st.session_state.dados_cliente['ato_90']
        
        total_entrada_cash = r1_val + r2_val + r3_val + r4_val
        st.session_state.dados_cliente['entrada_total'] = total_entrada_cash
        
        # Inclui o Volta ao Caixa na dedução do GAP FINAL
        gap_final = u_valor - f_u_input - fgts_u_input - ps_input_val - total_entrada_cash - vc_input_val
        if abs(gap_final) > 1.0: st.error(f"Atenção: {'Falta cobrir' if gap_final > 0 else 'Valor excedente de'} R$ {fmt_br(abs(gap_final))}.")
        parcela_fin = calcular_parcela_financiamento(f_u_input, prazo_finan, taxa_fin_vigente(d), tab_fin)
        st.session_state.dados_cliente['parcela_financiamento'] = parcela_fin
        st.markdown("---")
        if st.button("Avançar para Resumo da Simulação", type="primary", use_container_width=True):
            if abs(gap_final) <= 1.0: st.session_state.passo_simulacao = 'summary'; scroll_to_top(); st.rerun()
            else: st.error(f"Não é possível avançar. Saldo pendente: R$ {fmt_br(gap_final)}")
        st.markdown('<div data-btn-azul style="display:none" aria-hidden="true"></div>', unsafe_allow_html=True)
        if st.button("Voltar para Escolha de Unidade", use_container_width=True): st.session_state.passo_simulacao = 'selection'; scroll_to_top(); st.rerun()

    elif passo == 'summary':
        d = st.session_state.dados_cliente
        st.markdown(f"### Resumo da Simulação - {d.get('nome', 'Cliente')}")
        st.markdown(f'<div class="summary-header">DADOS DO IMÓVEL</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="summary-body">
            <b>Empreendimento:</b> {d.get('empreendimento_nome')}<br>
            <b>Unidade:</b> {d.get('unidade_id')}<br>
            <b>Valor Comercial (Venda):</b> <span style="color: {COR_VERMELHO}; font-weight: 800;">R$ {fmt_br(d.get('imovel_valor', 0))}</span><br>
            <b>Avaliação Bancária:</b> R$ {fmt_br(d.get('imovel_avaliacao', 0))}
        </div>""", unsafe_allow_html=True)
        
        # --- NOVO: EXIBIR DETALHES ADICIONAIS ---
        st.markdown(f'<div class="summary-header">DETALHES DA UNIDADE</div>', unsafe_allow_html=True)
        detalhes_html = f"""<div class="summary-body">"""
        if d.get('unid_entrega'): detalhes_html += f"<b>Previsão de Entrega:</b> {d.get('unid_entrega')}<br>"
        if d.get('unid_area'): detalhes_html += f"<b>Área Privativa Total:</b> {d.get('unid_area')} m²<br>"
        if d.get('unid_tipo'): detalhes_html += f"<b>Tipo Planta/Área:</b> {d.get('unid_tipo')}<br>"
        if d.get('unid_endereco') and d.get('unid_bairro'): 
            detalhes_html += f"<b>Localização:</b> {d.get('unid_endereco')} - {d.get('unid_bairro')}"
        detalhes_html += "</div>"
        st.markdown(detalhes_html, unsafe_allow_html=True)
        
        st.markdown(f'<div class="summary-header">PLANO DE FINANCIAMENTO</div>', unsafe_allow_html=True)
        prazo_txt = d.get('prazo_financiamento', 360)
        parcela_texto = f"Parcela Estimada ({d.get('sistema_amortizacao', 'SAC')} - {prazo_txt}x): R$ {fmt_br(d.get('parcela_financiamento', 0))}"
        st.markdown(f"""<div class="summary-body"><b>Financiamento Bancário:</b> R$ {fmt_br(d.get('finan_usado', 0))}<br><b>{parcela_texto}</b><br><b>FGTS + Subsídio:</b> R$ {fmt_br(d.get('fgts_sub_usado', 0))}<br><b>Pro Soluto Total:</b> R$ {fmt_br(d.get('ps_usado', 0))} ({d.get('ps_parcelas')}x de R$ {fmt_br(d.get('ps_mensal', 0))})</div>""", unsafe_allow_html=True)
        st.markdown(f'<div class="summary-header">FLUXO DE ENTRADA (ATO)</div>', unsafe_allow_html=True)
        st.markdown(f"""<div class="summary-body"><b>Total de Entrada:</b> R$ {fmt_br(d.get('entrada_total', 0))}<br><hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 10px 0;"><b>Ato:</b> R$ {fmt_br(d.get('ato_final', 0))}<br><b>Ato 30 Dias:</b> R$ {fmt_br(d.get('ato_30', 0))}<br><b>Ato 60 Dias:</b> R$ {fmt_br(d.get('ato_60', 0))}<br><b>Ato 90 Dias:</b> R$ {fmt_br(d.get('ato_90', 0))}</div>""", unsafe_allow_html=True)
        st.markdown("---")
        if st.button("Opções de Resumo (PDF / E-mail)", use_container_width=True): show_export_dialog(d)
        st.markdown("---")
        if st.button("CONCLUIR E SALVAR SIMULAÇÃO", type="primary", use_container_width=True):
            broker_email = st.session_state.get('user_email')
            if broker_email:
                with st.spinner("Gerando PDF e enviando para seu e-mail..."):
                    pdf_bytes_auto = gerar_resumo_pdf(d)
                    if pdf_bytes_auto:
                        sucesso_email, msg_email = enviar_email_smtp(broker_email, d.get('nome', 'Cliente'), pdf_bytes_auto, d, tipo='corretor')
                        if sucesso_email: st.toast("PDF enviado para seu e-mail com sucesso!", icon="📧")
                        else: st.toast(f"Falha no envio automático: {msg_email}", icon="⚠️")
            try:
                conn_save = st.connection("gsheets", type=GSheetsConnection)
                aba_destino = 'BD Simulações' 
                rendas_ind = d.get('rendas_lista', [])
                while len(rendas_ind) < 4: rendas_ind.append(0.0)
                capacidade_entrada = d.get('entrada_total', 0) + d.get('ps_usado', 0)
                nova_linha = {
                    "Nome": d.get('nome'), "CPF": d.get('cpf'), "Data de Nascimento": str(d.get('data_nascimento')),
                    "Prazo Financiamento": d.get('prazo_financiamento'), "Renda Part. 1": rendas_ind[0], "Renda Part. 4": rendas_ind[3],
                    "Renda Part. 3": rendas_ind[2], "Renda Part. 4.1": 0.0, "Ranking": d.get('ranking'),
                    "Política de Pro Soluto": d.get('politica'), "Fator Social": "Sim" if d.get('social') else "Não",
                    "Cotista FGTS": "Sim" if d.get('cotista') else "Não", "Financiamento Aprovado": d.get('finan_f_ref', 0),
                    "Subsídio Máximo": d.get('sub_f_ref', 0), "Pro Soluto Médio": d.get('ps_usado', 0), "Capacidade de Entrada": capacidade_entrada,
                    "Poder de Aquisição Médio": (2 * d.get('renda', 0)) + d.get('finan_f_ref', 0) + d.get('sub_f_ref', 0) + (d.get('imovel_valor', 0) * 0.10),
                    "Empreendimento Final": d.get('empreendimento_nome'), "Unidade Final": d.get('unidade_id'),
                    "Preço Unidade Final": d.get('imovel_valor', 0), "Financiamento Final": d.get('finan_usado', 0),
                    "FGTS + Subsídio Final": d.get('fgts_sub_usado', 0), "Pro Soluto Final": d.get('ps_usado', 0),
                    "Número de Parcelas do Pro Soluto": d.get('ps_parcelas', 0), "Mensalidade PS": d.get('ps_mensal', 0),
                    "Ato": d.get('ato_final', 0), "Ato 30": d.get('ato_30', 0), "Ato 60": d.get('ato_60', 0), "Ato 90": d.get('ato_90', 0),
                    "Renda Part. 2": rendas_ind[1], "Nome do Corretor": st.session_state.get('user_name', ''),
                    "Canal/Imobiliária": st.session_state.get('user_imobiliaria', ''),
                    "Data/Horário": datetime.now(pytz.timezone('America/Sao_Paulo')).strftime("%d/%m/%Y %H:%M:%S"),
                    "Sistema de Amortização": d.get('sistema_amortizacao', 'SAC'),
                    "Quantidade Parcelas Financiamento": d.get('prazo_financiamento', 360),
                    "Quantidade Parcelas Pro Soluto": d.get('ps_parcelas', 0),
                    "Volta ao Caixa": st.session_state.get('volta_caixa_key', 0.0) # Adicionado ao salvamento
                }
                df_novo = pd.DataFrame([nova_linha])
                try:
                    df_existente = conn_save.read(spreadsheet=ID_GERAL, worksheet=aba_destino)
                    df_final_save = pd.concat([df_existente, df_novo], ignore_index=True)
                except: df_final_save = df_novo
                conn_save.update(spreadsheet=ID_GERAL, worksheet=aba_destino, data=df_final_save)
                st.cache_data.clear()
                st.markdown(f'<div class="custom-alert">Salvo em \'{aba_destino}\'!</div>', unsafe_allow_html=True); time.sleep(2); st.session_state.dados_cliente = {}; st.session_state.passo_simulacao = 'input'; scroll_to_top(); st.rerun()
            except Exception as e: st.error(f"Erro ao salvar: {e}")
        st.markdown('<div data-btn-azul style="display:none" aria-hidden="true"></div>', unsafe_allow_html=True)
        if st.button("Voltar para Fechamento Financeiro", use_container_width=True): st.session_state.passo_simulacao = 'payment_flow'; scroll_to_top(); st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)

    # Botão Sair fora da coluna para herdar estilo grande
    st.markdown('<div data-btn-azul style="display:none" aria-hidden="true"></div>', unsafe_allow_html=True)
    if st.button("Sair do Sistema", key="btn_logout_bottom", use_container_width=True):
        st.session_state['logged_in'] = False
        st.rerun()

def main():
    configurar_layout()
    df_finan, df_estoque, df_politicas, df_logins, df_cadastros, _df_clientes, premissas_dict = carregar_dados_sistema()
    logo_src = URL_FAVICON_RESERVA
    if os.path.exists("favicon.png"):
        try:
            with open("favicon.png", "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
                logo_src = f"data:image/png;base64,{encoded}"
        except: pass
    st.markdown(f'''<div class="header-container"><img src="{logo_src}" style="position: absolute; top: 30px; left: 40px; height: 50px;"><div class="header-title">SIMULADOR IMOBILIÁRIO DV</div><div class="header-subtitle">Sistema de Gestão de Vendas e Viabilidade Imobiliária</div></div>''', unsafe_allow_html=True)

    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

    if not st.session_state['logged_in']: tela_login(df_logins)
    else: aba_simulador_automacao(df_finan, df_estoque, df_politicas, df_cadastros, premissas_dict)

    st.markdown(f'<div class="footer">Direcional Engenharia - Rio de Janeiro | Developed by Lucas Maia</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
