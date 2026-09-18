"""API de ejemplo que simula el sistema de origen de datos de empresas.

Sirve como "fuente de la verdad" para el prototipo: el script de Excel
y el loader de MySQL consumen estos mismos endpoints, en vez de leer
los datos simulados directamente, para que el flujo se parezca al de
un sistema real (API -> Excel / API -> base de datos -> Power BI).
"""
from __future__ import annotations

from collections import defaultdict
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from app.mock_data import EMPRESAS, FINANCIEROS, SBUS, ZONAS, empresas_por_id
from app.mock_oportunidades import CATALOGO_RESPONSABLES, CATALOGO_SE, OPORTUNIDADES

app = FastAPI(
    title="API de Empresas (datos simulados)",
    description="Representa un sistema fuente con datos de empresas reales de ejemplo, "
    "organizados por zona, oficina y SBU.",
    version="1.0.0",
)


class Empresa(BaseModel):
    id: int
    nombre: str
    rfc: str
    zona: str
    oficina: str
    sbu: str
    fecha_alta: str
    empleados: int
    activo: bool


class FinancieroMensual(BaseModel):
    id: int
    empresa_id: int
    anio: int
    mes: int
    ingresos: float
    costos: float
    utilidad_neta: float
    margen_neto: float


class ResumenGrupo(BaseModel):
    grupo: str
    num_empresas: int
    empleados_totales: int
    ingresos_totales: float
    costos_totales: float
    utilidad_neta_total: float
    margen_neto_promedio: float


GrupoPor = Literal["zona", "oficina", "sbu"]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/catalogos/zonas")
def catalogos_zonas():
    return {"zonas": {z: oficinas for z, oficinas in ZONAS.items()}}


@app.get("/catalogos/sbus")
def catalogos_sbus():
    return {"sbus": SBUS}


@app.get("/empresas", response_model=list[Empresa])
def listar_empresas(
    zona: Optional[str] = None,
    oficina: Optional[str] = None,
    sbu: Optional[str] = None,
    activo: Optional[bool] = None,
):
    resultado = EMPRESAS
    if zona:
        resultado = [e for e in resultado if e["zona"] == zona]
    if oficina:
        resultado = [e for e in resultado if e["oficina"] == oficina]
    if sbu:
        resultado = [e for e in resultado if e["sbu"] == sbu]
    if activo is not None:
        resultado = [e for e in resultado if e["activo"] == activo]
    return resultado


@app.get("/empresas/{empresa_id}", response_model=Empresa)
def obtener_empresa(empresa_id: int):
    empresa = empresas_por_id().get(empresa_id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return empresa


@app.get("/financieros", response_model=list[FinancieroMensual])
def listar_financieros(
    empresa_id: Optional[int] = None,
    anio: Optional[int] = None,
    mes: Optional[int] = None,
):
    resultado = FINANCIEROS
    if empresa_id is not None:
        resultado = [f for f in resultado if f["empresa_id"] == empresa_id]
    if anio is not None:
        resultado = [f for f in resultado if f["anio"] == anio]
    if mes is not None:
        resultado = [f for f in resultado if f["mes"] == mes]
    return resultado


@app.get("/financieros/resumen", response_model=list[ResumenGrupo])
def resumen_financiero(
    agrupar_por: GrupoPor = Query("zona", description="zona | oficina | sbu"),
    anio: Optional[int] = None,
    mes: Optional[int] = None,
):
    """Agregados listos para llenar el Excel: uno por zona / oficina / SBU."""
    empresas_idx = empresas_por_id()
    financieros = FINANCIEROS
    if anio is not None:
        financieros = [f for f in financieros if f["anio"] == anio]
    if mes is not None:
        financieros = [f for f in financieros if f["mes"] == mes]

    grupos: dict[str, dict] = defaultdict(
        lambda: {
            "empresas": set(),
            "ingresos_totales": 0.0,
            "costos_totales": 0.0,
            "utilidad_neta_total": 0.0,
            "margenes": [],
        }
    )

    for f in financieros:
        empresa = empresas_idx[f["empresa_id"]]
        clave = empresa[agrupar_por]
        g = grupos[clave]
        g["empresas"].add(empresa["id"])
        g["ingresos_totales"] += f["ingresos"]
        g["costos_totales"] += f["costos"]
        g["utilidad_neta_total"] += f["utilidad_neta"]
        g["margenes"].append(f["margen_neto"])

    salida = []
    for clave, g in grupos.items():
        empleados_totales = sum(empresas_idx[eid]["empleados"] for eid in g["empresas"])
        margen_prom = round(sum(g["margenes"]) / len(g["margenes"]), 2) if g["margenes"] else 0.0
        salida.append(
            ResumenGrupo(
                grupo=clave,
                num_empresas=len(g["empresas"]),
                empleados_totales=empleados_totales,
                ingresos_totales=round(g["ingresos_totales"], 2),
                costos_totales=round(g["costos_totales"], 2),
                utilidad_neta_total=round(g["utilidad_neta_total"], 2),
                margen_neto_promedio=margen_prom,
            )
        )
    return sorted(salida, key=lambda r: r.grupo)


# --- Oportunidades de venta (cobertura de soporte técnico) ---------------


class Oportunidad(BaseModel):
    id: int
    vendedor: str
    cuenta: str
    oportunidad: str
    etapa: str
    sbu: str
    mercado_vertical: str
    importe: float
    fecha_creacion: str
    periodo_fiscal: str
    anio_fiscal: int
    mes: int
    soporte_tecnico: Optional[str] = None


class ResponsableCatalogo(BaseModel):
    vendedor: str
    zona: Optional[str] = None
    oficina: Optional[str] = None


class SeCatalogo(BaseModel):
    vendedor: str
    se_responsable: Optional[str] = None


@app.get("/oportunidades", response_model=list[Oportunidad])
def listar_oportunidades(
    sbu: Optional[str] = None,
    etapa: Optional[str] = None,
    anio_fiscal: Optional[int] = None,
):
    resultado = OPORTUNIDADES
    if sbu:
        resultado = [o for o in resultado if o["sbu"] == sbu]
    if etapa:
        resultado = [o for o in resultado if o["etapa"] == etapa]
    if anio_fiscal is not None:
        resultado = [o for o in resultado if o["anio_fiscal"] == anio_fiscal]
    return resultado


@app.get("/catalogos/responsables", response_model=list[ResponsableCatalogo])
def catalogo_responsables():
    """Roster vendedor -> zona/oficina. Deliberadamente incompleto."""
    return CATALOGO_RESPONSABLES


@app.get("/catalogos/se", response_model=list[SeCatalogo])
def catalogo_se():
    """Roster vendedor -> responsable de soporte técnico. Deliberadamente incompleto."""
    return CATALOGO_SE
