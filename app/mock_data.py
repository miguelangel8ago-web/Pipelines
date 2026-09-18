"""Generador de datos simulados de empresas reales (zona / oficina / SBU).

Los datos se generan una sola vez, con semilla fija, para que cada
llamada a la API (y por lo tanto el llenado del Excel y la carga a
MySQL) sea reproducible entre corridas.
"""
from __future__ import annotations

import random
from datetime import date
from dateutil.relativedelta import relativedelta
from faker import Faker

SEED = 42

ZONAS = {
    "Norte": ["Monterrey", "Chihuahua"],
    "Centro": ["Ciudad de México", "Toluca"],
    "Bajío": ["Querétaro", "León"],
    "Sur": ["Mérida", "Villahermosa"],
    "Occidente": ["Guadalajara", "Puerto Vallarta"],
}

SBUS = [
    "Retail",
    "Manufactura",
    "Tecnología",
    "Servicios Financieros",
    "Energía",
    "Consumo Masivo",
]

N_EMPRESAS = 60
MESES_HISTORICO = 12


def _generar_empresas(fake: Faker) -> list[dict]:
    empresas = []
    zonas_lista = list(ZONAS.keys())
    for i in range(1, N_EMPRESAS + 1):
        zona = random.choice(zonas_lista)
        oficina = random.choice(ZONAS[zona])
        sbu = random.choice(SBUS)
        nombre = f"{fake.company()} S.A. de C.V."
        empresas.append(
            {
                "id": i,
                "nombre": nombre,
                "rfc": fake.bothify(text="???######???").upper(),
                "zona": zona,
                "oficina": oficina,
                "sbu": sbu,
                "fecha_alta": fake.date_between(start_date="-15y", end_date="-1y").isoformat(),
                "empleados": random.randint(15, 2500),
                "activo": random.random() > 0.08,
            }
        )
    return empresas


def _meses_historico() -> list[tuple[int, int]]:
    hoy = date.today().replace(day=1)
    periodos = []
    for offset in range(MESES_HISTORICO - 1, -1, -1):
        d = hoy - relativedelta(months=offset)
        periodos.append((d.year, d.month))
    return periodos


def _generar_financieros(empresas: list[dict]) -> list[dict]:
    registros = []
    periodos = _meses_historico()
    reg_id = 1
    for empresa in empresas:
        base_ingresos = random.uniform(500_000, 12_000_000)
        tendencia = random.uniform(-0.01, 0.02)
        for idx, (anio, mes) in enumerate(periodos):
            estacional = 1 + 0.08 * random.uniform(-1, 1)
            ingresos = round(base_ingresos * (1 + tendencia * idx) * estacional, 2)
            costos = round(ingresos * random.uniform(0.55, 0.85), 2)
            utilidad_neta = round(ingresos - costos, 2)
            margen_neto = round((utilidad_neta / ingresos) * 100, 2) if ingresos else 0.0
            registros.append(
                {
                    "id": reg_id,
                    "empresa_id": empresa["id"],
                    "anio": anio,
                    "mes": mes,
                    "ingresos": ingresos,
                    "costos": costos,
                    "utilidad_neta": utilidad_neta,
                    "margen_neto": margen_neto,
                }
            )
            reg_id += 1
    return registros


def _construir_dataset() -> tuple[list[dict], list[dict]]:
    random.seed(SEED)
    Faker.seed(SEED)
    fake = Faker("es_MX")
    empresas = _generar_empresas(fake)
    financieros = _generar_financieros(empresas)
    return empresas, financieros


EMPRESAS, FINANCIEROS = _construir_dataset()


def empresas_por_id() -> dict[int, dict]:
    return {e["id"]: e for e in EMPRESAS}
