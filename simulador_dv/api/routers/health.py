# -*- coding: utf-8 -*-
from fastapi import APIRouter

from simulador_dv.api.schemas import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    return HealthOut()
