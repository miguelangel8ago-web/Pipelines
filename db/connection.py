"""Construye el engine de SQLAlchemy a partir de variables de entorno.

Ver .env.example para las variables esperadas. Funciona igual con el
SQL Server de docker-compose (local) que con Azure SQL Database
(solo cambian host/usuario/clave y, en Azure, se fuerza el cifrado).

Requiere tener instalado el "ODBC Driver 18 for SQL Server" de Microsoft:
https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server
"""
from __future__ import annotations

import os
import urllib.parse

import pyodbc
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()


def _config():
    return {
        "driver": os.getenv("MSSQL_ODBC_DRIVER", "ODBC Driver 18 for SQL Server"),
        "host": os.getenv("MSSQL_HOST", "127.0.0.1"),
        "port": os.getenv("MSSQL_PORT", "1433"),
        "user": os.getenv("MSSQL_USER", "sa"),
        "password": os.getenv("MSSQL_PASSWORD", ""),
        "db": os.getenv("MSSQL_DATABASE", "pipelines_empresas"),
        # En Azure SQL el cifrado es obligatorio; en el contenedor local,
        # sin certificado real, hay que confiar en el autofirmado.
        "trust_cert": os.getenv("MSSQL_TRUST_SERVER_CERTIFICATE", "yes"),
    }


def _odbc_connection_string(database: str) -> str:
    c = _config()
    return (
        f"DRIVER={{{c['driver']}}};"
        f"SERVER={c['host']},{c['port']};"
        f"DATABASE={database};"
        f"UID={c['user']};PWD={c['password']};"
        f"Encrypt=yes;TrustServerCertificate={c['trust_cert']};"
    )


def ensure_database():
    """Crea la base de datos si no existe (Azure SQL ya la trae creada de por sí)."""
    c = _config()
    conn = pyodbc.connect(_odbc_connection_string("master"), autocommit=True)
    try:
        conn.execute(
            f"IF DB_ID(N'{c['db']}') IS NULL CREATE DATABASE [{c['db']}];"
        )
    finally:
        conn.close()


def get_engine():
    c = _config()
    odbc_params = urllib.parse.quote_plus(_odbc_connection_string(c["db"]))
    url = f"mssql+pyodbc:///?odbc_connect={odbc_params}"
    return create_engine(url, pool_pre_ping=True)


def get_session() -> Session:
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()
