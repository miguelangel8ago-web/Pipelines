# Crear Azure SQL Database (nivel gratuito) desde el portal

Guía para crear el servidor y la base que usará `db/connection.py`
(mismo código, solo cambia el `.env`).

## 1. Prerrequisito

Cuenta de Azure (https://azure.microsoft.com/free/) — no cuesta abrirla,
solo pide tarjeta para verificar identidad.

## 2. Crear el recurso

1. En https://portal.azure.com → **Crear un recurso** → busca **"Bases de
   datos SQL"** (SQL databases) → **Crear**.
2. **Pestaña "Conceptos básicos" (Basics)**:
   - **Suscripción**: la tuya (free trial o pay-as-you-go).
   - **Grupo de recursos**: crea uno nuevo, ej. `rg-pipelines`.
   - **Nombre de la base de datos**: `pipelines_empresas`.
   - **Servidor**: clic en **Crear nuevo**:
     - **Nombre del servidor**: algo único globalmente, ej.
       `sql-pipelines-<tu-nombre>` (queda como
       `sql-pipelines-<tu-nombre>.database.windows.net`).
     - **Ubicación**: la región más cercana (ej. `East US 2` o
       `Mexico Central` si ya está disponible).
     - **Método de autenticación**: **Usar autenticación SQL**.
     - **Inicio de sesión de administrador del servidor**: ej. `sqladmin`.
     - **Contraseña**: una segura (la vas a poner en `MSSQL_PASSWORD`).
   - **¿Usar grupo elástico SQL?**: No.
   - **Configuración de proceso + almacenamiento (Compute + storage)** →
     clic en **Configurar base de datos**:
     - Nivel de servicio: **General Purpose - Serverless**.
     - Debe aparecer la opción **"Aplicar oferta gratis" / "Apply free
       offer"** (solo si no la has usado antes en la suscripción) →
       actívala. Esto fija los límites gratuitos (32 GB, auto-pausa).
     - Guarda.
3. **Pestaña "Redes" (Networking)**:
   - **Método de conectividad**: **Punto de conexión público (Public
     endpoint)**.
   - **Reglas de firewall**:
     - **Permitir que los servicios y recursos de Azure obtengan acceso a
       este servidor** → **Sí** (necesario para que Power BI Service
       llegue sin Gateway).
     - **Agregar la dirección IP de cliente actual** → **Sí** (para poder
       conectarte tú desde tu PC/scripts).
4. **Pestaña "Seguridad" (Security)**: deja Microsoft Defender for SQL
   desactivado por ahora (tiene costo aparte, no es necesario para el
   prototipo).
5. **Pestaña "Configuración adicional" (Additional settings)**: Origen de
   datos = **Ninguno** (base vacía; nuestras tablas las crea
   `db/load_to_sqlserver.py`).
6. **Revisar y crear** → **Crear**. Espera a que termine el despliegue
   (unos minutos).

## 3. Obtener los datos de conexión

1. Ve al recurso creado (la base de datos, no el servidor) → **Overview**.
2. Copia el **"Server name"** (ej. `sql-pipelines-tunombre.database.windows.net`).
3. Actualiza tu `.env`:

```
MSSQL_HOST=sql-pipelines-tunombre.database.windows.net
MSSQL_PORT=1433
MSSQL_DATABASE=pipelines_empresas
MSSQL_USER=sqladmin
MSSQL_PASSWORD=<la contraseña que pusiste>
MSSQL_TRUST_SERVER_CERTIFICATE=no
```

## 4. Probar la conexión

```powershell
pipenv run python -m db.load_to_sqlserver
```

Si tu IP cambia (red doméstica dinámica) y te da error de conexión,
vuelve a **Redes** en el recurso del servidor y agrega tu IP actual a las
reglas de firewall.

## 5. Conectar Power BI

Ya no necesitas Gateway — sigue la **Opción B** de
[powerbi_gateway_setup.md](powerbi_gateway_setup.md).
