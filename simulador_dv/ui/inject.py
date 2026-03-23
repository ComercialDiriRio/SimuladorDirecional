# -*- coding: utf-8 -*-
"""
Carrega ficheiros estáticos (.css, .html, .js) e injeta no Streamlit.
Mantém app.py focado em lógica Python.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

_PKG_ROOT = Path(__file__).resolve().parents[1]
_ASSETS = _PKG_ROOT / "assets"


def _read_asset(relative_path: str) -> str:
    path = _ASSETS / relative_path.replace("/", Path.sep)
    if not path.is_file():
        raise FileNotFoundError(f"Asset não encontrado: {path}")
    return path.read_text(encoding="utf-8")


def inject_streamlit_styles() -> None:
    """Tema global + overrides de botão azul (equivalente ao <style> antigo em app.py)."""
    css_main = _read_asset("css/streamlit_theme.css")
    css_btn = _read_asset("css/streamlit_button_azul.css")
    st.markdown(f"<style>{css_main}\n{css_btn}</style>", unsafe_allow_html=True)


def scroll_to_top_component() -> None:
    """Scroll para o topo (iframe Streamlit)."""
    js = _read_asset("js/scroll_to_top.js")
    components.html(f"<script>{js}</script>", height=0)


def inject_gallery_modal() -> None:
    """HTML do modal da galeria + JavaScript (lightbox)."""
    html = _read_asset("html/gallery_modal.html")
    js = _read_asset("js/gallery_modal.js")
    st.markdown(f"{html}\n<script>{js}</script>", unsafe_allow_html=True)
