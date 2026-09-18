"""Datos simulados de oportunidades de venta con cobertura de soporte técnico.

Inspirado en un reporte real de Salesforce: las oportunidades se cruzan
contra dos catálogos mantenidos por separado (responsables → zona/oficina,
y responsables → SE/soporte técnico asignado). Ambos catálogos tienen
huecos A PROPÓSITO — vendedores que nunca se capturaron, o registros
incompletos (zona sin oficina, etc.) — para poder practicar la misma
lógica de auditoría de "descartadas" que describiste del reporte real.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from faker import Faker

from app.mock_data import ZONAS

SEED = 77

ETAPAS = [
    "E-Budgeting",
    "D-Bidding Purpose",
    "C-Under Negotiation",
    "B-Verbally Confirmed",
    "A-PO received",
    "W-Won",
    "Closed Lost",
    "Abandoned",
]
SBUS_OPORTUNIDADES = ["VRV", "Unitario", "Aplicado"]
MERCADOS_VERTICALES = [
    "Hotel",
    "Office Government",
    "Office Private",
    "Residential Apartments",
    "Residential Individual House",
    "Hospital Government",
    "Hospital Private",
    "Commercial (Stores, Banks, Restaurants)",
    "Industrial",
    "Education",
    "Stock Replenishment",
    "Others",
]

N_VENDEDORES = 40
N_SOPORTE_TECNICO = 12
N_OPORTUNIDADES = 400


def _generar_vendedores(fake: Faker) -> list[str]:
    return [fake.name() for _ in range(N_VENDEDORES)]


def _generar_catalogo_responsables(vendedores: list[str]) -> list[dict]:
    """vendedor -> zona/oficina. ~10% de los vendedores nunca se capturó
    aquí, y de los que sí, algunos quedan sin zona o sin oficina."""
    zonas_lista = list(ZONAS.keys())
    catalogo = []
    for vendedor in vendedores:
        if random.random() < 0.05:
            continue
        zona = random.choice(zonas_lista) if random.random() > 0.04 else None
        oficina = random.choice(ZONAS[zona]) if zona and random.random() > 0.05 else None
        catalogo.append({"vendedor": vendedor, "zona": zona, "oficina": oficina})
    return catalogo


def _generar_catalogo_se(vendedores: list[str], nombres_soporte: list[str]) -> list[dict]:
    """vendedor -> se_responsable. Roster mantenido aparte, con sus propios huecos."""
    catalogo = []
    for vendedor in vendedores:
        if random.random() < 0.05:
            continue
        se = random.choice(nombres_soporte) if random.random() > 0.04 else None
        catalogo.append({"vendedor": vendedor, "se_responsable": se})
    return catalogo


def _periodo_fiscal(fecha: date) -> tuple[str, int]:
    """Año fiscal empieza en octubre (T1 = oct-dic), como en el reporte real."""
    anio_fiscal = fecha.year + (1 if fecha.month >= 10 else 0)
    trimestre = ((fecha.month - 10) % 12) // 3 + 1
    return f"T{trimestre}-{anio_fiscal}", anio_fiscal


def _generar_oportunidades(fake: Faker, vendedores: list[str], nombres_soporte: list[str]) -> list[dict]:
    hoy = date.today()
    oportunidades = []
    for i in range(1, N_OPORTUNIDADES + 1):
        vendedor = random.choice(vendedores)
        etapa = random.choice(ETAPAS)
        sbu = random.choice(SBUS_OPORTUNIDADES)
        mercado_vertical = random.choice(MERCADOS_VERTICALES)
        importe = round(random.uniform(1_000, 500_000), 2) if random.random() > 0.05 else 0.0
        fecha_creacion = hoy - timedelta(days=random.randint(0, 180))
        periodo_fiscal, anio_fiscal = _periodo_fiscal(fecha_creacion)
        soporte_tecnico = random.choice(nombres_soporte) if random.random() > 0.35 else None
        oportunidades.append(
            {
                "id": i,
                "vendedor": vendedor,
                "cuenta": f"{fake.company()}",
                "oportunidad": f"OP-{sbu}-{i:04d}",
                "etapa": etapa,
                "sbu": sbu,
                "mercado_vertical": mercado_vertical,
                "importe": importe,
                "fecha_creacion": fecha_creacion.isoformat(),
                "periodo_fiscal": periodo_fiscal,
                "anio_fiscal": anio_fiscal,
                "mes": fecha_creacion.month,
                "soporte_tecnico": soporte_tecnico,
            }
        )
    return oportunidades


def _construir_dataset():
    random.seed(SEED)
    Faker.seed(SEED)
    fake = Faker("es_MX")
    vendedores = _generar_vendedores(fake)
    nombres_soporte = [fake.name() for _ in range(N_SOPORTE_TECNICO)]
    catalogo_responsables = _generar_catalogo_responsables(vendedores)
    catalogo_se = _generar_catalogo_se(vendedores, nombres_soporte)
    oportunidades = _generar_oportunidades(fake, vendedores, nombres_soporte)
    return oportunidades, catalogo_responsables, catalogo_se


OPORTUNIDADES, CATALOGO_RESPONSABLES, CATALOGO_SE = _construir_dataset()
