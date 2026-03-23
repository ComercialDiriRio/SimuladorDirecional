# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Request, Response

from simulador_dv.api.deps import resolve_session_id
from simulador_dv.api.estado_helpers import estado_sessao_out
from simulador_dv.api.schemas_flow import EstadoSessaoOut, SessionCreatedOut, SessionCreateIn, SessionPatchIn
from simulador_dv.api.session_store import (
    SESSION_COOKIE_NAME,
    create_session,
    delete_session,
    get_session,
    update_session,
)

router = APIRouter(prefix="/session", tags=["session"])


def _to_out(st: Dict[str, Any]) -> EstadoSessaoOut:
    return estado_sessao_out(st)


@router.post("", response_model=SessionCreatedOut)
def create_session_ep(body: SessionCreateIn, response: Response) -> SessionCreatedOut:
    sid = create_session(email=body.email)
    st = get_session(sid)
    assert st is not None
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=sid,
        httponly=True,
        samesite="lax",
        max_age=86400 * 7,
        path="/",
    )
    return SessionCreatedOut(session_id=sid, estado=_to_out(st))


@router.get("", response_model=EstadoSessaoOut)
def get_session_ep(
    request: Request,
    x_session_id: Optional[str] = Header(default=None, alias="X-Session-Id"),
) -> EstadoSessaoOut:
    sid = resolve_session_id(request, x_session_id)
    if not sid:
        raise HTTPException(status_code=401, detail="Sessão necessária")
    st = get_session(sid)
    if st is None:
        raise HTTPException(status_code=401, detail="Sessão inválida")
    return _to_out(st)


@router.patch("", response_model=EstadoSessaoOut)
def patch_session_ep(
    request: Request,
    body: SessionPatchIn,
    x_session_id: Optional[str] = Header(default=None, alias="X-Session-Id"),
) -> EstadoSessaoOut:
    sid = resolve_session_id(request, x_session_id)
    if not sid:
        raise HTTPException(status_code=401, detail="Sessão necessária")
    patch = body.model_dump(exclude_unset=True)
    st = update_session(sid, patch)
    if st is None:
        raise HTTPException(status_code=401, detail="Sessão inválida")
    return _to_out(st)


@router.delete("")
def delete_session_ep(
    request: Request,
    response: Response,
    x_session_id: Optional[str] = Header(default=None, alias="X-Session-Id"),
) -> Dict[str, str]:
    sid = resolve_session_id(request, x_session_id)
    if sid:
        delete_session(sid)
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return {"ok": "true"}
