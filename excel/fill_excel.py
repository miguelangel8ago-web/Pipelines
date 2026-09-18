"""Llena la plantilla de Excel con datos leídos desde la API.

Lógica de llenado (ejemplo, ajustable cuando se defina la lógica final):
    - Resumen: KPIs agregados de TODAS las empresas.
    - Zona / Oficina / SBU: cada hoja ya trae sus filas (una por zona,
      oficina o SBU); el script busca la fila por el nombre y solo
      escribe las columnas de métricas, sin tocar la estructura.
    - Detalle Empresas: agrega una fila por empresa activa con su
      acumulado de ingresos/costos/utilidad de los últimos 12 meses.

No se sobrescribe la plantilla: el resultado se guarda en un archivo
de salida aparte (reporte_empresas_<fecha>.xlsx).
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import requests
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from excel.generate_template import DATA_METRIC_COLS, PLANTILLA_PATH

API_BASE_URL = "http://127.0.0.1:8000"
SALIDA_DIR = Path(__file__).parent / "salidas"

METRICA_A_CAMPO = {
    "# Empresas": "num_empresas",
    "Empleados": "empleados_totales",
    "Ingresos Totales": "ingresos_totales",
    "Costos Totales": "costos_totales",
    "Utilidad Neta": "utilidad_neta_total",
    "Margen Neto %": "margen_neto_promedio",
}


def _get(path: str, **params) -> dict | list:
    resp = requests.get(f"{API_BASE_URL}{path}", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _col_de_encabezado(ws: Worksheet, titulo: str) -> int:
    for celda in ws[1]:
        if celda.value == titulo:
            return celda.column
    raise ValueError(f"No se encontró la columna '{titulo}' en la hoja '{ws.title}'")


def _fila_por_etiqueta(ws: Worksheet, col_etiqueta: int, etiqueta: str) -> int:
    for fila in range(2, ws.max_row + 1):
        if ws.cell(row=fila, column=col_etiqueta).value == etiqueta:
            return fila
    raise ValueError(f"No se encontró la etiqueta '{etiqueta}' en la hoja '{ws.title}'")


def _llenar_hoja_grupo(ws: Worksheet, agrupar_por: str, col_etiqueta_titulo: str):
    resumen = _get("/financieros/resumen", agrupar_por=agrupar_por)
    col_etiqueta = _col_de_encabezado(ws, col_etiqueta_titulo)
    columnas_metricas = {m: _col_de_encabezado(ws, m) for m in DATA_METRIC_COLS}

    for grupo in resumen:
        fila = _fila_por_etiqueta(ws, col_etiqueta, grupo["grupo"])
        for metrica, campo in METRICA_A_CAMPO.items():
            ws.cell(row=fila, column=columnas_metricas[metrica], value=grupo[campo])


def _llenar_resumen(ws: Worksheet):
    empresas = _get("/empresas", activo=True)
    resumen_zonas = _get("/financieros/resumen", agrupar_por="zona")

    ingresos_totales = sum(g["ingresos_totales"] for g in resumen_zonas)
    costos_totales = sum(g["costos_totales"] for g in resumen_zonas)
    utilidad_total = sum(g["utilidad_neta_total"] for g in resumen_zonas)
    empleados_totales = sum(g["empleados_totales"] for g in resumen_zonas)
    margen_promedio = (
        round(sum(g["margen_neto_promedio"] for g in resumen_zonas) / len(resumen_zonas), 2)
        if resumen_zonas
        else 0.0
    )

    ws["B2"] = date.today().isoformat()
    valores = {
        "Total de Empresas": len(empresas),
        "Empleados Totales": empleados_totales,
        "Ingresos Totales (MXN)": round(ingresos_totales, 2),
        "Costos Totales (MXN)": round(costos_totales, 2),
        "Utilidad Neta Total (MXN)": round(utilidad_total, 2),
        "Margen Neto Promedio (%)": margen_promedio,
    }
    for fila in range(1, ws.max_row + 1):
        etiqueta = ws.cell(row=fila, column=1).value
        if etiqueta in valores:
            ws.cell(row=fila, column=2, value=valores[etiqueta])


def _llenar_detalle_empresas(ws: Worksheet):
    empresas = _get("/empresas", activo=True)
    fila = 2
    for empresa in empresas:
        financieros = _get("/financieros", empresa_id=empresa["id"])
        ingresos = sum(f["ingresos"] for f in financieros)
        costos = sum(f["costos"] for f in financieros)
        utilidad = ingresos - costos
        margen = round((utilidad / ingresos) * 100, 2) if ingresos else 0.0
        valores = [
            empresa["nombre"],
            empresa["rfc"],
            empresa["zona"],
            empresa["oficina"],
            empresa["sbu"],
            empresa["empleados"],
            round(ingresos, 2),
            round(costos, 2),
            round(utilidad, 2),
            margen,
        ]
        for col_idx, valor in enumerate(valores, start=1):
            ws.cell(row=fila, column=col_idx, value=valor)
        fila += 1


def llenar_reporte(plantilla_path: Path = PLANTILLA_PATH) -> Path:
    if not plantilla_path.exists():
        raise FileNotFoundError(
            f"No existe la plantilla en {plantilla_path}. Corre generate_template.py primero."
        )

    wb = load_workbook(plantilla_path)
    _llenar_resumen(wb["Resumen"])
    _llenar_hoja_grupo(wb["Zona"], "zona", "Zona")
    _llenar_hoja_grupo(wb["Oficina"], "oficina", "Oficina")
    _llenar_hoja_grupo(wb["SBU"], "sbu", "SBU")
    _llenar_detalle_empresas(wb["Detalle Empresas"])

    SALIDA_DIR.mkdir(parents=True, exist_ok=True)
    salida_path = SALIDA_DIR / f"reporte_empresas_{date.today().isoformat()}.xlsx"
    wb.save(salida_path)
    return salida_path


if __name__ == "__main__":
    try:
        ruta = llenar_reporte()
    except requests.exceptions.ConnectionError:
        print(
            "No se pudo conectar a la API. Levántala primero con:\n"
            "    uvicorn app.main:app --reload",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"Reporte generado en: {ruta}")
