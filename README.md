# Pipelines — Empresas: API → pandas → Data Warehouse → Power BI

Pipeline de extremo a extremo:

```
FastAPI (datos simulados de empresas)
   │
   ├──> Excel (plantilla llenada por zona/oficina/SBU)
   │
   └──> pandas (etl/)                      ← transforma y modela
          │
          ▼
        SQL Server / Azure SQL              ← esquema estrella (6 tablas)
          │
          ▼
        Vistas (db/views.py)                ← DirectQuery
          │
          ▼
        Power BI
```

## Instalación

```powershell
pipenv install
```

## 1. Levantar la API de datos

```powershell
pipenv run uvicorn app.main:app --reload
```

Explora `http://127.0.0.1:8000/docs` para ver los endpoints.

## 2. Generar la plantilla de Excel (una sola vez)

```powershell
pipenv run python -m excel.generate_template
```

Crea `excel/plantilla_empresas.xlsx` con las pestañas Resumen / Zona /
Oficina / SBU / Detalle Empresas, sin datos.

## 3. Llenar el Excel con datos de la API

Con la API corriendo:

```powershell
pipenv run python -m excel.fill_excel
```

Genera `excel/salidas/reporte_empresas_<fecha>.xlsx`. La lógica de qué
celda se llena con qué dato vive en `excel/fill_excel.py` — es la que se
debe ajustar cuando definas las reglas exactas de negocio.

## 4. Cargar el data warehouse (SQL Server / Azure SQL)

Requiere tener instalado el **ODBC Driver 18 for SQL Server** de Microsoft
(https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server).

```powershell
docker compose up -d          # o usa Azure SQL / SQL Server local
copy .env.example .env        # y ajusta credenciales (o las de Azure SQL)
pipenv run python -m db.load_to_sqlserver
```

Esto corre el pipeline completo:

1. **Extrae** (`etl/extract.py`) empresas y financieros de la API.
2. **Transforma con pandas** (`etl/transform.py`) hacia un **esquema
   estrella**: separa dimensiones (`dim_zona`, `dim_oficina`, `dim_sbu`,
   `dim_empresa`, `dim_tiempo`) del hecho (`fact_financieros`, un
   renglón por empresa/mes), generando las llaves subrogadas.
3. **Recarga** las 6 tablas en SQL Server (full refresh en cada corrida).
4. **Publica 5 vistas** (`db/views.py`) listas para **Power BI por
   DirectQuery**: `vw_resumen_zona`, `vw_resumen_oficina`,
   `vw_resumen_sbu`, `vw_tendencia_mensual`, `vw_detalle_financiero`.

## 5. Conectar Power BI

Ver [docs/powerbi_gateway_setup.md](docs/powerbi_gateway_setup.md) para el
paso a paso de instalar el On-premises Data Gateway y publicar el dataset,
o [docs/azure_sql_setup.md](docs/azure_sql_setup.md) si vas por Azure SQL
(conexión directa, sin Gateway).

## Estructura

```
app/        FastAPI + generador de datos simulados
excel/      Plantilla y script de llenado
etl/        Extracción (API → pandas) y transformación al modelo estrella
db/         Modelos SQLAlchemy (esquema estrella), vistas, y el loader
docs/       Guías de Power BI Gateway, Azure SQL, y Git
```

## El modelo de datos

```
dim_zona ──┐
           ├──< dim_oficina
dim_zona ──┘         │
dim_sbu ─────────────┼──< dim_empresa ──< fact_financieros >── dim_tiempo
```

- **`dim_empresa`**: una fila por empresa (nombre, rfc, empleados, fechas), con llaves a zona/oficina/sbu.
- **`dim_tiempo`**: un renglón por periodo (año, mes, trimestre, nombre de mes).
- **`fact_financieros`**: ingresos/costos/utilidad/margen por empresa y mes — la tabla que crece.
- Las vistas de resumen (`vw_resumen_*`) agregan primero por empresa y
  luego por grupo, para no inflar campos como `empleados` al sumarlos
  una vez por cada uno de los 12 meses del hecho.
