# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Annotated, Any, Dict, Optional

from fastapi import Depends, Header, HTTPException, Request

from simulador_dv.api.session_store import SESSION_COOKIE_NAME, get_session


def resolve_session_id(
    request: Request,
    x_session_id: Optional[str] = Header(default=None, alias="X-Session-Id"),
) -> Optional[str]:
    if x_session_id:
        return x_session_id.strip()
    return request.cookies.get(SESSION_COOKIE_NAME)


def require_session_state(
    request: Request,
    x_session_id: Optional[str] = Header(default=None, alias="X-Session-Id"),
) -> Dict[str, Any]:
    sid = resolve_session_id(request, x_session_id)
    if not sid:
        raise HTTPException(status_code=401, detail="Sessão necessária. Faça POST /api/session ou login.")
    st = get_session(sid)
    if st is None:
        raise HTTPException(status_code=401, detail="Sessão expirada ou inválida.")
    # Injeta _session_id para routers atualizarem estado
    out = dict(st)
    out["_session_id"] = sid
    return out


def require_admin(st: Annotated[dict, Depends(require_session_state)]) -> dict:
    """Sessão com coluna ADM?=SIM na BD Logins."""
    if not st.get("is_admin"):
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return st
