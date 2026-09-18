"""Vistas del modelo dimensional, pensadas para conectarse a Power BI
por DirectQuery.

Cada vista se crea con `CREATE OR ALTER VIEW`, que exige SQL Server:
debe ser la ÚNICA sentencia de su lote — por eso cada una se ejecuta
por separado en `load_to_sqlserver.py`, nunca concatenadas.

Nota de diseño: `vw_resumen_zona`, `_oficina` y `_sbu` agregan en DOS
pasos (un CTE que primero resume por empresa, y luego el SELECT final
que agrupa por zona/oficina/sbu). Si se agregara todo de un solo golpe,
`empleados` se sumaría una vez por cada uno de los 12 meses de esa
empresa en `fact_financieros`, inflando el total 12x.
"""

VISTAS: dict[str, str] = {
    "vw_resumen_zona": """
CREATE OR ALTER VIEW vw_resumen_zona AS
WITH financiero_por_empresa AS (
    SELECT
        empresa_id,
        SUM(ingresos)      AS ingresos_totales,
        SUM(costos)        AS costos_totales,
        SUM(utilidad_neta) AS utilidad_neta_total,
        AVG(margen_neto)   AS margen_neto_promedio
    FROM fact_financieros
    GROUP BY empresa_id
)
SELECT
    z.zona,
    COUNT(*)                     AS num_empresas,
    SUM(e.empleados)             AS empleados_totales,
    SUM(f.ingresos_totales)      AS ingresos_totales,
    SUM(f.costos_totales)        AS costos_totales,
    SUM(f.utilidad_neta_total)   AS utilidad_neta_total,
    AVG(f.margen_neto_promedio)  AS margen_neto_promedio
FROM dim_empresa e
JOIN dim_zona z ON z.zona_id = e.zona_id
JOIN financiero_por_empresa f ON f.empresa_id = e.empresa_id
GROUP BY z.zona;
""",
    "vw_resumen_oficina": """
CREATE OR ALTER VIEW vw_resumen_oficina AS
WITH financiero_por_empresa AS (
    SELECT
        empresa_id,
        SUM(ingresos)      AS ingresos_totales,
        SUM(costos)        AS costos_totales,
        SUM(utilidad_neta) AS utilidad_neta_total,
        AVG(margen_neto)   AS margen_neto_promedio
    FROM fact_financieros
    GROUP BY empresa_id
)
SELECT
    z.zona,
    o.oficina,
    COUNT(*)                     AS num_empresas,
    SUM(e.empleados)             AS empleados_totales,
    SUM(f.ingresos_totales)      AS ingresos_totales,
    SUM(f.costos_totales)        AS costos_totales,
    SUM(f.utilidad_neta_total)   AS utilidad_neta_total,
    AVG(f.margen_neto_promedio)  AS margen_neto_promedio
FROM dim_empresa e
JOIN dim_oficina o ON o.oficina_id = e.oficina_id
JOIN dim_zona z ON z.zona_id = o.zona_id
JOIN financiero_por_empresa f ON f.empresa_id = e.empresa_id
GROUP BY z.zona, o.oficina;
""",
    "vw_resumen_sbu": """
CREATE OR ALTER VIEW vw_resumen_sbu AS
WITH financiero_por_empresa AS (
    SELECT
        empresa_id,
        SUM(ingresos)      AS ingresos_totales,
        SUM(costos)        AS costos_totales,
        SUM(utilidad_neta) AS utilidad_neta_total,
        AVG(margen_neto)   AS margen_neto_promedio
    FROM fact_financieros
    GROUP BY empresa_id
)
SELECT
    s.sbu,
    COUNT(*)                     AS num_empresas,
    SUM(e.empleados)             AS empleados_totales,
    SUM(f.ingresos_totales)      AS ingresos_totales,
    SUM(f.costos_totales)        AS costos_totales,
    SUM(f.utilidad_neta_total)   AS utilidad_neta_total,
    AVG(f.margen_neto_promedio)  AS margen_neto_promedio
FROM dim_empresa e
JOIN dim_sbu s ON s.sbu_id = e.sbu_id
JOIN financiero_por_empresa f ON f.empresa_id = e.empresa_id
GROUP BY s.sbu;
""",
    "vw_tendencia_mensual": """
CREATE OR ALTER VIEW vw_tendencia_mensual AS
SELECT
    t.anio,
    t.mes,
    t.nombre_mes,
    t.trimestre,
    COUNT(DISTINCT f.empresa_id) AS empresas_activas,
    SUM(f.ingresos)              AS ingresos_totales,
    SUM(f.costos)                AS costos_totales,
    SUM(f.utilidad_neta)         AS utilidad_neta_total,
    AVG(f.margen_neto)           AS margen_neto_promedio
FROM fact_financieros f
JOIN dim_tiempo t ON t.fecha_id = f.fecha_id
GROUP BY t.anio, t.mes, t.nombre_mes, t.trimestre;
""",
    "vw_detalle_financiero": """
CREATE OR ALTER VIEW vw_detalle_financiero AS
SELECT
    f.id AS fact_id,
    e.empresa_id,
    e.nombre AS empresa,
    e.rfc,
    z.zona,
    o.oficina,
    s.sbu,
    e.empleados,
    e.activo,
    t.anio,
    t.mes,
    t.nombre_mes,
    t.trimestre,
    f.ingresos,
    f.costos,
    f.utilidad_neta,
    f.margen_neto
FROM fact_financieros f
JOIN dim_empresa e ON e.empresa_id = f.empresa_id
JOIN dim_zona z ON z.zona_id = e.zona_id
JOIN dim_oficina o ON o.oficina_id = e.oficina_id
JOIN dim_sbu s ON s.sbu_id = e.sbu_id
JOIN dim_tiempo t ON t.fecha_id = f.fecha_id;
""",
    "vw_cobertura_tse": """
CREATE OR ALTER VIEW vw_cobertura_tse AS
SELECT
    zona,
    oficina,
    mercado_vertical,
    sbu,
    anio_fiscal,
    mes,
    COUNT(*)                                                            AS num_oportunidades,
    SUM(CASE WHEN soporte_tecnico IS NOT NULL THEN 1 ELSE 0 END)        AS oportunidades_con_soporte,
    CAST(SUM(CASE WHEN soporte_tecnico IS NOT NULL THEN 1 ELSE 0 END) AS FLOAT)
        / COUNT(*) * 100                                                AS cobertura_pct,
    SUM(importe)                                                        AS importe_total,
    SUM(CASE WHEN soporte_tecnico IS NOT NULL THEN importe ELSE 0 END)  AS importe_con_soporte,
    CASE WHEN SUM(importe) = 0 THEN 0 ELSE
        SUM(CASE WHEN soporte_tecnico IS NOT NULL THEN importe ELSE 0 END)
        / SUM(importe) * 100
    END                                                                  AS cobertura_importe_pct
FROM fact_oportunidades
GROUP BY zona, oficina, mercado_vertical, sbu, anio_fiscal, mes;
""",
}
