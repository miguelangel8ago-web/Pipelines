"""Extrae los datos crudos de la API hacia DataFrames de pandas.

Es la parte "E" del ETL: solo trae los datos tal cual los da la API,
sin transformarlos todavía (eso es trabajo de transform.py).
"""
from __future__ import annotations

import pandas as pd
import requests

API_BASE_URL = "http://127.0.0.1:8000"


def _get(path: str, **params) -> list[dict]:
    resp = requests.get(f"{API_BASE_URL}{path}", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def extraer_empresas() -> pd.DataFrame:
    return pd.DataFrame(_get("/empresas"))


def extraer_financieros() -> pd.DataFrame:
    return pd.DataFrame(_get("/financieros"))


def extraer_oportunidades() -> pd.DataFrame:
    return pd.DataFrame(_get("/oportunidades"))


def extraer_catalogo_responsables() -> pd.DataFrame:
    return pd.DataFrame(_get("/catalogos/responsables"))


def extraer_catalogo_se() -> pd.DataFrame:
    return pd.DataFrame(_get("/catalogos/se"))
