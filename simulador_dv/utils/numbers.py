# -*- coding: utf-8 -*-
from __future__ import annotations


def safe_float(val) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0
