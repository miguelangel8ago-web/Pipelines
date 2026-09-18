"""Orquesta el pipeline de oportunidades de venta:

    1. Extrae oportunidades y los dos catálogos (responsables, SE) de la API.
    2. Los cruza con pandas (etl/transform.py::auditar_oportunidades):
       separa las oportunidades válidas de las descartadas, con el motivo
       de cada descarte — igual que el `Audit_Descartadas` del reporte real.
    3. Recarga ambas tablas en SQL Server / Azure SQL (full refresh).
    4. Publica la vista de cobertura de soporte técnico para Power BI.
"""
from __future__ import annotations

import sys

import requests
from sqlalchemy import text

from db.connection import ensure_database, get_engine
from db.models import Base
from db.views import VISTAS
from etl.extract import (
    extraer_catalogo_responsables,
    extraer_catalogo_se,
    extraer_oportunidades,
)
from etl.transform import auditar_oportunidades

TABLAS_EN_ORDEN_DE_BORRADO = ["fact_oportunidades", "audit_oportunidades_descartadas"]

VISTA_COBERTURA = "vw_cobertura_tse"


def cargar():
    ensure_database()
    engine = get_engine()
    Base.metadata.create_all(engine)

    print("Extrayendo oportunidades y catálogos de la API...")
    oportunidades = extraer_oportunidades()
    catalogo_responsables = extraer_catalogo_responsables()
    catalogo_se = extraer_catalogo_se()

    print("Cruzando contra catálogos (pandas) y separando válidas/descartadas...")
    validas, descartadas = auditar_oportunidades(oportunidades, catalogo_responsables, catalogo_se)

    print("Recargando tablas en SQL Server...")
    with engine.begin() as conn:
        for tabla in TABLAS_EN_ORDEN_DE_BORRADO:
            conn.execute(text(f"DELETE FROM {tabla}"))

    validas.to_sql("fact_oportunidades", engine, if_exists="append", index=False)
    descartadas.to_sql("audit_oportunidades_descartadas", engine, if_exists="append", index=False)

    print("Creando vista de cobertura TSE para Power BI...")
    with engine.begin() as conn:
        conn.execute(text(VISTAS[VISTA_COBERTURA]))

    cobertura = 100 * validas["soporte_tecnico"].notna().mean() if len(validas) else 0.0
    print(
        f"Listo: {len(validas)} oportunidades válidas, {len(descartadas)} descartadas "
        f"(de {len(oportunidades)} totales)."
    )
    print(f"Cobertura de soporte técnico en las válidas: {cobertura:.1f}%")
    print(f"Vista: {VISTA_COBERTURA}")


if __name__ == "__main__":
    try:
        cargar()
    except requests.exceptions.ConnectionError:
        print(
            "No se pudo conectar a la API. Levántala primero con:\n"
            "    uvicorn app.main:app --reload",
            file=sys.stderr,
        )
        sys.exit(1)
