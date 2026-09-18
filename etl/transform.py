"""Transforma los DataFrames crudos de la API al modelo dimensional (estrella).

Es la parte "T" del ETL — aquí es donde pandas hace el trabajo real:
separa las dimensiones (zona, oficina, sbu, tiempo, empresa) del hecho
(financieros), genera las llaves subrogadas (`*_id`) y arma las
relaciones entre tablas, todo antes de que nada toque SQL Server.
"""
from __future__ import annotations

import pandas as pd

NOMBRES_MES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def construir_dim_zona(empresas: pd.DataFrame) -> pd.DataFrame:
    zonas = sorted(empresas["zona"].unique())
    return pd.DataFrame({"zona_id": range(1, len(zonas) + 1), "zona": zonas})


def construir_dim_sbu(empresas: pd.DataFrame) -> pd.DataFrame:
    sbus = sorted(empresas["sbu"].unique())
    return pd.DataFrame({"sbu_id": range(1, len(sbus) + 1), "sbu": sbus})


def construir_dim_oficina(empresas: pd.DataFrame, dim_zona: pd.DataFrame) -> pd.DataFrame:
    oficinas = empresas[["zona", "oficina"]].drop_duplicates()
    oficinas = oficinas.merge(dim_zona, on="zona").sort_values("oficina").reset_index(drop=True)
    oficinas["oficina_id"] = range(1, len(oficinas) + 1)
    return oficinas[["oficina_id", "oficina", "zona_id"]]


def construir_dim_tiempo(financieros: pd.DataFrame) -> pd.DataFrame:
    periodos = (
        financieros[["anio", "mes"]]
        .drop_duplicates()
        .sort_values(["anio", "mes"])
        .reset_index(drop=True)
    )
    periodos["fecha_id"] = periodos["anio"] * 100 + periodos["mes"]
    periodos["trimestre"] = ((periodos["mes"] - 1) // 3) + 1
    periodos["nombre_mes"] = periodos["mes"].map(NOMBRES_MES)
    return periodos[["fecha_id", "anio", "mes", "trimestre", "nombre_mes"]]


def construir_dim_empresa(
    empresas: pd.DataFrame,
    dim_zona: pd.DataFrame,
    dim_oficina: pd.DataFrame,
    dim_sbu: pd.DataFrame,
) -> pd.DataFrame:
    df = (
        empresas
        .merge(dim_zona, on="zona")
        .merge(dim_oficina[["oficina_id", "oficina"]], on="oficina")
        .merge(dim_sbu, on="sbu")
    )
    df["fecha_alta"] = pd.to_datetime(df["fecha_alta"]).dt.date
    return df[
        ["id", "nombre", "rfc", "empleados", "activo", "fecha_alta", "zona_id", "oficina_id", "sbu_id"]
    ].rename(columns={"id": "empresa_id"})


def construir_fact_financieros(financieros: pd.DataFrame, dim_tiempo: pd.DataFrame) -> pd.DataFrame:
    df = financieros.merge(dim_tiempo[["fecha_id", "anio", "mes"]], on=["anio", "mes"])
    return df[["id", "empresa_id", "fecha_id", "ingresos", "costos", "utilidad_neta", "margen_neto"]]


# --- Oportunidades: cruce contra catálogos + auditoría de descartadas ----

MOTIVOS_DESCARTE = {
    "descartada_zona": "vendedor_sin_zona",
    "descartada_oficina": "vendedor_sin_oficina",
    "descartada_se": "vendedor_sin_se_responsable",
    "descartada_importe": "importe_menor_o_igual_a_0",
}


def auditar_oportunidades(
    oportunidades: pd.DataFrame,
    catalogo_responsables: pd.DataFrame,
    catalogo_se: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Cruza cada oportunidad contra los catálogos de responsables y de SE,
    igual que en el reporte real: si el vendedor no aparece en un catálogo
    (o el registro está incompleto), la oportunidad se marca como
    descartada con el motivo correspondiente, y no entra al análisis.

    Regresa (validas, descartadas) — dos DataFrames separados, el segundo
    con las columnas de auditoría (`descartada_*` y `motivos`) listas para
    una hoja de Excel o tabla de auditoría, tal como el `Audit_Descartadas`
    del reporte real.
    """
    df = oportunidades.merge(catalogo_responsables, on="vendedor", how="left")
    df = df.merge(catalogo_se, on="vendedor", how="left")
    df["fecha_creacion"] = pd.to_datetime(df["fecha_creacion"]).dt.date

    df["descartada_zona"] = df["zona"].isna()
    df["descartada_oficina"] = df["oficina"].isna()
    df["descartada_se"] = df["se_responsable"].isna()
    df["descartada_importe"] = df["importe"] <= 0

    columnas_check = list(MOTIVOS_DESCARTE.keys())

    def _motivos(fila):
        return " | ".join(MOTIVOS_DESCARTE[c] for c in columnas_check if fila[c])

    df["motivos"] = df.apply(_motivos, axis=1)
    descartada = df[columnas_check].any(axis=1)

    validas = df.loc[~descartada].drop(columns=columnas_check + ["motivos"]).reset_index(drop=True)
    descartadas = df.loc[descartada].reset_index(drop=True)
    return validas, descartadas
