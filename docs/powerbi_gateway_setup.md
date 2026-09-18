# Conectar SQL Server / Azure SQL a Power BI

Hay dos caminos, según dónde viva la base de datos:

- **Local (docker-compose / SQL Server instalado a mano):** necesitas el
  **On-premises Data Gateway**, porque Power BI Service (en la nube) no
  puede llegar por sí solo a tu red local.
- **Azure SQL Database:** es una base en la nube, así que Power BI se
  conecta **directo**, sin Gateway — solo necesitas abrir el firewall de
  Azure SQL para permitir el tráfico de Power BI.

A diferencia de MySQL, el conector de **SQL Server viene nativo** tanto en
Power BI Desktop como en el Gateway — no hace falta instalar un driver
aparte.

## Opción A — Base local (Gateway)

1. Instalar el **On-premises Data Gateway**:
   https://powerbi.microsoft.com/en-us/gateway/
   - Inicia sesión con la cuenta de Microsoft/Entra ID de tu organización
     (la misma que usas en Power BI Service).
   - Elige modo "On-premises data gateway" (no el modo personal).
2. En https://app.powerbi.com → ⚙️ **Settings** → **Manage gateways** →
   selecciona tu gateway → **Add data source**:
   - **Data Source Type**: SQL Server
   - **Server**: `<host>,<puerto>` (ej. `localhost,1433` si el Gateway
     corre en la misma máquina que el contenedor)
   - **Database**: `pipelines_empresas`
   - **Authentication**: SQL Server Authentication → usuario/clave de
     `MSSQL_USER` / `MSSQL_PASSWORD` del `.env`
3. En **Users**, agrega a quienes vayan a usar esta conexión.
4. En Power BI Desktop → **Obtener datos** → **SQL Server** → mismo
   servidor/BD → en el modo de conectividad elige **DirectQuery** (no
   Import, para que las consultas se ejecuten en vivo contra SQL Server
   en vez de cargar una copia) → selecciona las vistas que necesites de
   `db/views.py`:
   - `vw_resumen_zona`, `vw_resumen_oficina`, `vw_resumen_sbu` — ya
     agregadas, ideales para tarjetas/KPIs y gráficas de barras.
   - `vw_tendencia_mensual` — para gráficas de línea de tiempo.
   - `vw_detalle_financiero` — la tabla plana (una fila por empresa/mes),
     para tablas de detalle o análisis libre en Power BI.
5. Publica el `.pbix` → en el dataset publicado → **Settings** →
   **Gateway connection** → asocia el gateway y la fuente del paso 2.
6. Con DirectQuery no hay "Scheduled refresh" que configurar de datos —
   cada visual consulta SQL Server en el momento; solo asegúrate de que
   el Gateway esté siempre encendido.

## Opción B — Azure SQL Database (sin Gateway)

1. Crea el servidor lógico y la base (nivel gratuito "serverless" si
   aplica) desde el portal de Azure.
2. En el portal de Azure → tu servidor SQL → **Networking** → habilita
   **"Allow Azure services and resources to access this server"** (y, si
   quieres administrarla desde tu PC, agrega tu IP a las reglas de
   firewall).
3. En Power BI Desktop → **Obtener datos** → **Azure SQL Database** →
   pega el nombre del servidor (`<servidor>.database.windows.net`) y la
   base → modo de conectividad **DirectQuery** → elige las vistas que
   necesites (mismas de la Opción A: `vw_resumen_zona`,
   `vw_resumen_oficina`, `vw_resumen_sbu`, `vw_tendencia_mensual`,
   `vw_detalle_financiero`).
4. Publica el `.pbix`. Como es una fuente en la nube y DirectQuery
   consulta en vivo, no hace falta configurar ningún gateway ni refresh
   programado de datos.

## Notas sobre costo y despliegue

- **Docker local**: $0, pero solo accesible en tu red — de ahí la
  necesidad del Gateway.
- **Azure SQL Database serverless "always free"**: gratis de forma
  permanente dentro de sus límites (100,000 vCore-segundos/mes, 32 GB),
  una base gratuita por suscripción. Pasado ese límite, se cobra por
  consumo.
- **Migrar de local a Azure**: como ambos son SQL Server, un backup/restore
  (`.bacpac` con SqlPackage, o scripts de `sqlcmd`) mueve el esquema y los
  datos sin cambios de código — el proyecto ya lee host/usuario/clave desde
  `.env`.
