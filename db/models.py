"""Modelo dimensional (esquema estrella) para el data warehouse de empresas.

Dimensiones:
    DimZona, DimOficina, DimSbu, DimEmpresa, DimTiempo
Hecho:
    FactFinanciero — un renglón por empresa/mes.

Las llaves de las dimensiones NO son autoincrementales: las genera
`etl/transform.py` con pandas antes de cargar, así que aquí se marcan
explícitamente `autoincrement=False` (si no, SQL Server las crearía
como columnas IDENTITY y el `to_sql` con valores explícitos fallaría).

Power BI nunca consulta estas tablas directamente — se conecta a las
vistas de `db/views.py`, pensadas para DirectQuery.
"""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class DimZona(Base):
    __tablename__ = "dim_zona"

    zona_id = Column(Integer, primary_key=True, autoincrement=False)
    zona = Column(String(50), nullable=False, unique=True)


class DimSbu(Base):
    __tablename__ = "dim_sbu"

    sbu_id = Column(Integer, primary_key=True, autoincrement=False)
    sbu = Column(String(50), nullable=False, unique=True)


class DimOficina(Base):
    __tablename__ = "dim_oficina"

    oficina_id = Column(Integer, primary_key=True, autoincrement=False)
    oficina = Column(String(50), nullable=False)
    zona_id = Column(Integer, ForeignKey("dim_zona.zona_id"), nullable=False)

    zona = relationship("DimZona")


class DimTiempo(Base):
    __tablename__ = "dim_tiempo"

    fecha_id = Column(Integer, primary_key=True, autoincrement=False)  # formato AAAAMM, ej. 202609
    anio = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    trimestre = Column(Integer, nullable=False)
    nombre_mes = Column(String(15), nullable=False)


class DimEmpresa(Base):
    __tablename__ = "dim_empresa"

    empresa_id = Column(Integer, primary_key=True, autoincrement=False)
    nombre = Column(String(255), nullable=False)
    rfc = Column(String(20), nullable=False)
    empleados = Column(Integer, nullable=False)
    activo = Column(Boolean, nullable=False)
    fecha_alta = Column(Date, nullable=False)
    zona_id = Column(Integer, ForeignKey("dim_zona.zona_id"), nullable=False)
    oficina_id = Column(Integer, ForeignKey("dim_oficina.oficina_id"), nullable=False)
    sbu_id = Column(Integer, ForeignKey("dim_sbu.sbu_id"), nullable=False)

    zona = relationship("DimZona")
    oficina = relationship("DimOficina")
    sbu = relationship("DimSbu")


class FactFinanciero(Base):
    __tablename__ = "fact_financieros"
    __table_args__ = (UniqueConstraint("empresa_id", "fecha_id", name="uq_empresa_fecha"),)

    id = Column(Integer, primary_key=True, autoincrement=False)
    empresa_id = Column(Integer, ForeignKey("dim_empresa.empresa_id"), nullable=False)
    fecha_id = Column(Integer, ForeignKey("dim_tiempo.fecha_id"), nullable=False)
    ingresos = Column(Float, nullable=False)
    costos = Column(Float, nullable=False)
    utilidad_neta = Column(Float, nullable=False)
    margen_neto = Column(Float, nullable=False)

    empresa = relationship("DimEmpresa")
    tiempo = relationship("DimTiempo")


# --- Oportunidades de venta con cobertura de soporte técnico -------------
# Estas dos tablas son el resultado de etl/transform.py::auditar_oportunidades:
# las oportunidades que sí cruzaron bien contra los catálogos van a
# FactOportunidad; las que no, a AuditOportunidadDescartada con el motivo.


class FactOportunidad(Base):
    __tablename__ = "fact_oportunidades"

    id = Column(Integer, primary_key=True, autoincrement=False)
    vendedor = Column(String(100), nullable=False)
    cuenta = Column(String(255), nullable=False)
    oportunidad = Column(String(50), nullable=False)
    etapa = Column(String(30), nullable=False)
    sbu = Column(String(20), nullable=False)
    mercado_vertical = Column(String(60), nullable=False)
    importe = Column(Float, nullable=False)
    fecha_creacion = Column(Date, nullable=False)
    periodo_fiscal = Column(String(10), nullable=False)
    anio_fiscal = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    soporte_tecnico = Column(String(100), nullable=True)
    zona = Column(String(50), nullable=False)
    oficina = Column(String(50), nullable=False)
    se_responsable = Column(String(100), nullable=False)


class AuditOportunidadDescartada(Base):
    __tablename__ = "audit_oportunidades_descartadas"

    id = Column(Integer, primary_key=True, autoincrement=False)
    vendedor = Column(String(100), nullable=False)
    cuenta = Column(String(255), nullable=False)
    oportunidad = Column(String(50), nullable=False)
    etapa = Column(String(30), nullable=False)
    sbu = Column(String(20), nullable=False)
    mercado_vertical = Column(String(60), nullable=False)
    importe = Column(Float, nullable=False)
    fecha_creacion = Column(Date, nullable=False)
    periodo_fiscal = Column(String(10), nullable=False)
    anio_fiscal = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    soporte_tecnico = Column(String(100), nullable=True)
    zona = Column(String(50), nullable=True)
    oficina = Column(String(50), nullable=True)
    se_responsable = Column(String(100), nullable=True)
    descartada_zona = Column(Boolean, nullable=False)
    descartada_oficina = Column(Boolean, nullable=False)
    descartada_se = Column(Boolean, nullable=False)
    descartada_importe = Column(Boolean, nullable=False)
    motivos = Column(String(255), nullable=False)
