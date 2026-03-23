# -*- coding: utf-8 -*-
"""Armazenamento de sessão em memória (substitui st.session_state na API)."""
from __future__ import annotations

import copy
import uuid
from typing import Any, Dict, Optional

SESSION_COOKIE_NAME = "sim_session_id"

# session_id -> estado
_STORE: Dict[str, Dict[str, Any]] = {}


def default_session_state(email: Optional[str] = None) -> Dict[str, Any]:
    return {
        "email": email,
        "passo_simulacao": "input",
        "dados_cliente": {},
        "cliente_ativo": False,
        "session_ui": {},
        "unidade_selecionada": None,
        "user_name": None,
        "user_phone": None,
        "user_imobiliaria": None,
        "user_cargo": None,
    }


def create_session(email: Optional[str] = None, extra: Optional[Dict[str, Any]] = None) -> str:
    sid = str(uuid.uuid4())
    state = default_session_state(email=email)
    if extra:
        state.update(extra)
    _STORE[sid] = state
    return sid


def get_session(sid: str) -> Optional[Dict[str, Any]]:
    return _STORE.get(sid)


def delete_session(sid: str) -> None:
    _STORE.pop(sid, None)


def update_session(sid: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    st = _STORE.get(sid)
    if st is None:
        return None
    if "dados_cliente" in patch and isinstance(patch["dados_cliente"], dict):
        dc = copy.deepcopy(st.get("dados_cliente") or {})
        dc.update(patch["dados_cliente"])
        st["dados_cliente"] = dc
        patch = {k: v for k, v in patch.items() if k != "dados_cliente"}
    if "session_ui" in patch and isinstance(patch["session_ui"], dict):
        su = copy.deepcopy(st.get("session_ui") or {})
        su.update(patch["session_ui"])
        st["session_ui"] = su
        patch = {k: v for k, v in patch.items() if k != "session_ui"}
    for k, v in patch.items():
        if k in ("dados_cliente", "session_ui"):
            continue
        if v is None:
            continue
        st[k] = v
    return st


def clear_store_for_tests() -> None:
    _STORE.clear()
