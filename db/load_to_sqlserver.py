"""Orquesta el pipeline completo:

    1. Extrae empresas y financieros de la API (etl/extract.py).
    2. Los transforma con pandas al modelo dimensional — dimensiones +
       hecho (etl/transform.py).
    3. Recarga las tablas en SQL Server / Azure SQL (full refresh: se
       limpian y se vuelven a insertar completas en cada corrida, lo
       más simple y confiable para datos reproducibles como estos).
    4. Publica las vistas de Power BI (db/views.py).
"""
from __future__ import annotations

import sys

import requests
from sqlalchemy import text

from db.connection import ensure_database, get_engine
from db.models import Base
from db.views import VISTAS
from etl.extract import extraer_empresas, extraer_financieros
from etl.transform import (
    construir_dim_empresa,
    construir_dim_oficina,
    construir_dim_sbu,
    construir_dim_tiempo,
    construir_dim_zona,
    construir_fact_financieros,
)

# Orden de borrado: primero el hecho y las dimensiones que dependen de
# otras, para no violar las llaves foráneas.
TABLAS_EN_ORDEN_DE_BORRADO = [
    "fact_financieros",
    "dim_empresa",
    "dim_oficina",
    "dim_zona",
    "dim_sbu",
    "dim_tiempo",
]


def cargar():
    ensure_database()
    engine = get_engine()
    Base.metadata.create_all(engine)

    print("Extrayendo empresas y financieros de la API...")
    empresas_df = extraer_empresas()
    financieros_df = extraer_financieros()

    print("Transformando con pandas al modelo dimensional...")
    dim_zona = construir_dim_zona(empresas_df)
    dim_sbu = construir_dim_sbu(empresas_df)
    dim_oficina = construir_dim_oficina(empresas_df, dim_zona)
    dim_tiempo = construir_dim_tiempo(financieros_df)
    dim_empresa = construir_dim_empresa(empresas_df, dim_zona, dim_oficina, dim_sbu)
    fact_financieros = construir_fact_financieros(financieros_df, dim_tiempo)

    print("Recargando tablas en SQL Server...")
    with engine.begin() as conn:
        for tabla in TABLAS_EN_ORDEN_DE_BORRADO:
            conn.execute(text(f"DELETE FROM {tabla}"))

    dim_zona.to_sql("dim_zona", engine, if_exists="append", index=False)
    dim_sbu.to_sql("dim_sbu", engine, if_exists="append", index=False)
    dim_tiempo.to_sql("dim_tiempo", engine, if_exists="append", index=False)
    dim_oficina.to_sql("dim_oficina", engine, if_exists="append", index=False)
    dim_empresa.to_sql("dim_empresa", engine, if_exists="append", index=False)
    fact_financieros.to_sql("fact_financieros", engine, if_exists="append", index=False)

    print("Creando vistas para Power BI (DirectQuery)...")
    with engine.begin() as conn:
        for nombre, sql in VISTAS.items():
            conn.execute(text(sql))

    print(
        f"Listo: {len(dim_empresa)} empresas, {len(fact_financieros)} registros financieros, "
        f"{len(dim_zona)} zonas, {len(dim_oficina)} oficinas, {len(dim_sbu)} SBUs, "
        f"{len(dim_tiempo)} periodos."
    )
    print("Vistas: " + ", ".join(VISTAS.keys()))


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
