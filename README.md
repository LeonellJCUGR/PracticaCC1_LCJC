# RutaTicket — Venta de entradas para atractivos turísticos

Aplicación Nativa de la Nube (*Cloud-Native Application*) para una pequeña empresa turística que vende entradas para visitar atractivos turísticos (miradores, rutas guiadas, monumentos, museos), con **precios por temporada** (descuentos en temporada baja o campañas especiales) y **control de aforo diario**. Desplegado sobre **Microsoft Azure**.

---

## Índice

1. [Descripción del dominio](#1-descripción-del-dominio)
2. [Casos de uso principales](#2-casos-de-uso-principales)
3. [Justificación NIST SP 800-145](#3-justificación-nist-sp-800-145)
4. [Mapeo de actores NIST SP 500-292](#4-mapeo-de-actores-nist-sp-500-292)
5. [Arquitectura de referencia](#5-arquitectura-de-referencia)
6. [Especificación de la API REST](#6-especificación-de-la-api-rest)
7. [Hito 2: contenedores, entorno local e integración continua](#7-hito-2-contenedores-entorno-local-e-integración-continua)

---

## 1. Descripción del dominio

### Problema de negocio

Una pequeña empresa turística gestiona la venta de entradas a varios atractivos de su zona. Hoy lo hace de forma manual (taquilla y hojas de cálculo),
lo que provoca tres problemas:

1. **Sobreventa**: no hay control en tiempo real del aforo diario de cada atractivo, por lo que se venden más entradas de las permitidas.
2. **Precios incoherentes**: los descuentos de temporada (temporada baja, campañas puntuales) se aplican a mano y con errores.
3. **Demanda muy estacional**: en Semana Santa, verano o puentes el tráfico se multiplica, mientras que en temporada baja casi no hay ventas. Mantener servidores propios dimensionados para el pico sería caro e infrautilizado el resto del año.

### Solución

**RutaTicket** permite consultar atractivos, calcular el precio final según la fecha de visita (aplicando automáticamente el descuento de temporada vigente), comprar entradas sin superar el aforo diario, cancelarlas con antelación y validarlas en la puerta mediante un código único.

### Lógica de negocio

| Regla | Descripción |
|---|---|
| **RN-01 Precio por temporada** | `precio_unitario = precio_base × (1 − descuento / 100)`. Si en una fecha coinciden varias temporadas, se aplica la de **mayor descuento**. Sin temporada vigente, se cobra el precio base. |
| **RN-02 Control de aforo** | Una compra solo se confirma si `entradas_vendidas(atracción, fecha) + cantidad ≤ aforo_diario`. |
| **RN-03 Fechas válidas** | No se pueden comprar entradas para fechas pasadas ni con más de 90 días de antelación. Máximo 10 entradas por compra. |
| **RN-04 Cancelación** | Una reserva `CONFIRMADA` puede cancelarse hasta **24 h antes** de la fecha de visita; las plazas vuelven al aforo disponible. |
| **RN-05 Validación de acceso** | Cada reserva tiene un código único. Solo puede validarse el **día de la visita** y **una única vez** (pasa a estado `USADA`). |

Ciclo de vida de una reserva:

![alt text](CicloVidaReserva.png)


## 2. Casos de uso principales

| ID | Actor | Caso de uso |
|---|---|---|
| CU-01 | Administrador | Dar de alta/modificar atractivos (nombre, precio base, aforo diario). |
| CU-02 | Administrador | Definir temporadas de descuento (rango de fechas y porcentaje). |
| CU-03 | Visitante | Consultar el catálogo de atractivos y el precio final para una fecha. |
| CU-04 | Visitante | Comprar entradas para una fecha (con control de aforo). |
| CU-05 | Visitante | Consultar y cancelar su reserva. |
| CU-06 | Empleado de taquilla | Validar el código de la entrada en el acceso. |
| CU-07 | Administrador | Consultar estadísticas de ventas e ingresos por atractivo. |

## 3. Justificación NIST SP 800-145

**Modelo de servicio:** PaaS (Azure Container Apps y Azure SQL Database). **Modelo de despliegue:** nube pública (Microsoft Azure, región *Spain Central* / *West Europe*).

| Característica esencial | Cómo la aprovecha RutaTicket |
|---|---|
| **Autoservicio bajo demanda** | Toda la infraestructura (Container Apps y Azure SQL Database) se aprovisiona sin intervención humana del proveedor, mediante Terraform y el pipeline de GitHub Actions. Crear un entorno nuevo es ejecutar `terraform apply`. |
| **Acceso amplio a la red** | Los servicios exponen una API REST sobre HTTPS accesible desde cualquier cliente estándar: web del visitante, móvil del empleado de taquilla para validar entradas o la herramienta del administrador. |
| **Asignación común de recursos (*pooling*)** | Los contenedores se ejecutan sobre la infraestructura multiinquilino de Azure Container Apps; la base de datos es un servicio gestionado compartido físicamente con otros clientes, aislado lógicamente. La empresa no sabe (ni necesita saber) en qué servidor físico se ejecuta. |
| **Rápida elasticidad** | Container Apps escala horizontalmente por número de peticiones HTTP concurrentes (p. ej. de 0 a 5 réplicas). En temporada alta o al lanzar una campaña de descuentos se absorbe el pico; en temporada baja se escala a **cero réplicas**. |
| **Servicio medido** | Se paga por vCPU-segundo, GiB-segundo y peticiones consumidas en Container Apps, y por vCore-segundo y GB de almacenamiento en Azure SQL Database (nivel *serverless*). Azure Monitor / Cost Management permiten medir y controlar el consumo. |

## 4. Mapeo de actores NIST SP 500-292

| Rol NIST | Quién es en RutaTicket | Responsabilidad |
|---|---|---|
| **Consumidor (*Cloud Consumer*)** | La empresa turística (en el proyecto, el alumno que la opera). Indirectamente, sus clientes usan la aplicación. | Contrata servicios PaaS de Azure, despliega la aplicación y paga por uso. |
| **Proveedor (*Cloud Provider*)** | Microsoft Azure. | Ofrece cómputo (Container Apps), base de datos gestionada (Azure SQL Database), red y registro de logs; garantiza SLA, parches y seguridad física. |
| **Intermediario (*Cloud Broker*)** | En un escenario real, un *partner* CSP (*Cloud Solution Provider*) de Microsoft o Azure Marketplace. | Intermediación: agrega facturación, soporte y asesoramiento a la pyme sin personal de TI propio. |
| **Auditor (*Cloud Auditor*)** | Auditor externo de cumplimiento (RGPD/AEPD, ISO 27001 o ENS). Herramientas de apoyo: Microsoft Defender for Cloud y Azure Policy. | Evalúa de forma independiente la seguridad, la privacidad de los datos de los visitantes y el rendimiento. |
| **Operador (*Cloud Carrier*)** | Proveedores de acceso a Internet (de los visitantes y de la empresa) y la red troncal global de Microsoft. | Transporta las peticiones HTTPS entre clientes y los centros de datos de Azure. |

### Impacto económico

- **De CapEx a OpEx**: la empresa no compra servidores ni licencias; paga mensualmente solo lo que consume. Para una pyme con demanda estacional esto evita sobredimensionar para el pico de verano.
- **Escalado a cero**: en temporada baja Container Apps puede quedarse sin réplicas activas, por lo que el coste de cómputo tiende a cero. Además, Container Apps incluye una cuota gratuita mensual de vCPU-segundos, GiB-segundos y peticiones que cubre holgadamente un tráfico pequeño.
- **Base de datos *serverless***: Azure SQL Database en nivel *serverless* se pausa automáticamente cuando no recibe consultas y solo cobra cómputo mientras está activa. Se usa **un único servidor lógico con dos bases de datos** (`catalog_db` y `booking_db`), manteniendo el patrón *database-per-service*.
- **Coste del proyecto**: la [oferta gratuita de Azure SQL Database](https://learn.microsoft.com/azure/azure-sql/database/free-offer) incluye hasta 10 bases de datos por suscripción, cada una con 100.000 vCore-segundos y 32 GB al mes, configuradas para pausarse al agotar la cuota en lugar de facturar. Junto con la cuota gratuita de Container Apps, el coste del proyecto es prácticamente nulo. Los recursos se destruyen con `terraform destroy` cuando no se usan.
- **Coste de los intermediarios**: un partner CSP (Cloud Solution Provider) añadiría un margen sobre la factura de Azure a cambio de soporte; para una pyme sin informático puede compensar.

## 5. Arquitectura de referencia

La aplicación se divide en **2 microservicios independientes** con su propia base de datos lógica. Cada uno se empaqueta como contenedor Docker y se despliega por separado.

| Componente | Responsabilidad | Tecnología |
|---|---|---|
| **catalog-service** (Catálogo y Precios) | Atractivos, temporadas de descuento y cálculo del precio final (RN-01). | Python 3.12 + FastAPI |
| **booking-service** (Reservas) | Compra, cancelación y validación de entradas; control de aforo (RN-02 a RN-05); estadísticas de ventas. | Python 3.12 + FastAPI |
| **Persistencia** | `catalog_db` y `booking_db` en el mismo servidor lógico. | Azure SQL Database (*serverless*, oferta gratuita) |

### Diagrama

![alt text](ArquitecturaDeNegocio.png)

### Protocolos de comunicación

| Origen → Destino | Protocolo  | Tipo |
|---|---|---|
| Clientes → microservicios | HTTPS (TLS terminado en el *ingress* de Container Apps), REST + JSON | Síncrono |
| booking-service → catalog-service | HTTP REST + JSON por la red interna del Container Apps Environment | Síncrono |
| Microservicios → Azure SQL Database | Protocolo TDS (SQL Server) sobre TCP 1433 con TLS, vía SQLAlchemy + `pyodbc` | Síncrono |
| GitHub Actions → GHCR / Azure | HTTPS (token de GitHub / *service principal*) | Despliegue |

**Flujo de compra (CU-04):**

![alt text](FlujoCompras.png)

### Decisiones clave

- **Solo 2 microservicios**: separan dos contextos de negocio claros (qué se vende y a qué precio / quién compra y cuándo). Más servicios añadirían complejidad sin valor para el alcance del curso.
- **Comunicación REST síncrona**: suficiente para el volumen de una pyme; evita introducir un *broker* de mensajería.
- **Sin caché**: el enunciado exige persistencia **o** caché; Azure SQL Database cubre el requisito. Si en el Hito 5 las pruebas de carga lo justifican, se valorará cachear las respuestas de `/precios`.
- **Registro de imágenes en GitHub (GHCR)**: gratuito e integrado con GitHub Actions; evita crear y pagar un Azure Container Registry.
- **Secretos mínimos y seguros**: en local, fichero `.env` ignorado por `.gitignore`; en el pipeline, *GitHub Secrets*; en Azure, los **secretos de Container Apps** inyectados como variables de entorno (`DATABASE_URL`). No se usa Key Vault para no añadir otro recurso.
- **Log Analytics**: obligatorio para crear el Container Apps Environment; se reutiliza para la observabilidad del Hito 5.
- **IaC con Terraform** (Hito 3) y **CI/CD con GitHub Actions** (Hitos 2 y 4).

## 6. Especificación de la API REST

Prefijo común: `/api/v1`. Formato: JSON. Fechas en ISO 8601 (`YYYY-MM-DD`). Importes en euros con 2 decimales. Ambos servicios exponen `GET /health` para las sondas de Container Apps.

### 6.1 catalog-service

| Verbo  | Ruta                                             | Descripción                     | Respuestas    |
|--------|--------------------------------------------------|---------------------------------|---------------|
| GET    | `/api/v1/atracciones`                            | Lista atractivos activos        | 200           |
| GET    | `/api/v1/atracciones/{id}`                       | Detalle de un atractivo         | 200, 404      |
| POST   | `/api/v1/atracciones`                            | Crea un atractivo (admin)       | 201, 422      |
| PUT    | `/api/v1/atracciones/{id}`                       | Modifica un atractivo (admin)   | 200, 404, 422 |
| GET    | `/api/v1/temporadas`                             | Lista temporadas de descuento   | 200           |
| POST   | `/api/v1/temporadas`                             | Crea una temporada (admin)      | 201, 422      |
| DELETE | `/api/v1/temporadas/{id}`                        | Elimina una temporada (admin)   | 204, 404      |
| GET    | `/api/v1/precios?atraccion_id=&fecha=&cantidad=` | Calcula el precio final (RN-01) | 200, 404, 422 |

`POST /api/v1/atracciones` — petición:

```json
{
  "nombre": "Mirador del Valle",
  "descripcion": "Visita guiada al mirador",
  "precio_base": 12.00,
  "aforo_diario": 150
}
```

Respuesta `201`:

```json
{
  "id": 1,
  "nombre": "Mirador del Valle",
  "descripcion": "Visita guiada al mirador",
  "precio_base": 12.00,
  "aforo_diario": 150,
  "activa": true
}
```

`POST /api/v1/temporadas` — petición:

```json
{
  "nombre": "Temporada baja invierno",
  "fecha_inicio": "2026-11-01",
  "fecha_fin": "2027-02-28",
  "descuento_porcentaje": 20
}
```

`GET /api/v1/precios?atraccion_id=1&fecha=2026-11-15&cantidad=3` — respuesta `200`:

```json
{
  "atraccion_id": 1,
  "fecha": "2026-11-15",
  "cantidad": 3,
  "precio_base": 12.00,
  "temporada": "Temporada baja invierno",
  "descuento_porcentaje": 20,
  "precio_unitario": 9.60,
  "total": 28.80,
  "aforo_diario": 150
}
```

### 6.2 booking-service

| Verbo| Ruta | Descripción | Respuestas |
|---|---|---|---|
| GET | `/api/v1/disponibilidad?atraccion_id=&fecha=` | Plazas libres para una fecha | 200, 404 |
| POST | `/api/v1/reservas` | Compra entradas (RN-02, RN-03) | 201, 404, 409, 422 |
| GET | `/api/v1/reservas/{codigo}`                        | Consulta una reserva                   | 200, 404           |
| POST | `/api/v1/reservas/{codigo}/cancelacion`            | Cancela la reserva (RN-04)             | 200, 404, 409      |
| POST | `/api/v1/reservas/{codigo}/validacion`             | Valida la entrada en el acceso (RN-05) | 200, 404, 409      |
| GET | `/api/v1/estadisticas/ventas?desde=&hasta=`        | Ventas e ingresos por atractivo (admin)| 200                |

`POST /api/v1/reservas` — petición:

```json
{
  "atraccion_id": 1,
  "fecha_visita": "2026-11-15",
  "cantidad": 3,
  "cliente": {
    "nombre": "Ana López",
    "email": "ana@example.com"
  }
}
```

Respuesta `201`:

```json
{
  "codigo": "RT-7F3K9Q",
  "atraccion_id": 1,
  "fecha_visita": "2026-11-15",
  "cantidad": 3,
  "precio_unitario": 9.60,
  "total": 28.80,
  "estado": "CONFIRMADA",
  "creada_en": "2026-10-20T10:35:00Z"
}
```

Respuesta `409` (aforo completo):

```json
{
  "error": "AFORO_COMPLETO",
  "detalle": "Solo quedan 2 plazas para el 2026-11-15"
}
```

`POST /api/v1/reservas/RT-7F3K9Q/validacion` — respuesta `200`:

```json
{ "codigo": "RT-7F3K9Q", "estado": "USADA", "validada_en": "2026-11-15T09:12:00Z" }
```

`GET /api/v1/estadisticas/ventas?desde=2026-11-01&hasta=2026-11-30` — respuesta `200`:

```json
{
  "desde": "2026-11-01",
  "hasta": "2026-11-30",
  "total_entradas": 412,
  "ingresos_totales": 3955.20,
  "por_atraccion": [
    { "atraccion_id": 1, "entradas": 300, "ingresos": 2880.00, "ocupacion_media": 0.67 },
    { "atraccion_id": 2, "entradas": 112, "ingresos": 1075.20, "ocupacion_media": 0.37 }
  ]
}
```

## 7. Hito 2: contenedores, entorno local e integración continua

### Estructura del repositorio

```
.
├── services/
│   ├── catalog-service/          # FastAPI: atractivos, temporadas y precios (RN-01)
│   │   ├── app/                  # código (main, routers, models, schemas, pricing)
│   │   ├── tests/unit/           # lógica pura de precios
│   │   ├── tests/integration/    # API HTTP + persistencia (SQLite en memoria)
│   │   ├── Dockerfile
│   │   └── requirements*.txt
│   └── booking-service/          # FastAPI: reservas, aforo, cancelación, validación (RN-02..05)
│       └── (misma estructura; app/reglas.py contiene las reglas de negocio puras)
├── gateway/                      # API Gateway (NGINX): único punto de entrada
│   ├── nginx/gateway.conf        # enrutado, rate limiting, cabeceras y errores JSON
│   └── Dockerfile
├── tests/e2e/                    # integración de sistema (a través del gateway)
├── db/init/init-db.sql           # script parametrizado: crea la BD y el login de un servicio
├── compose.yaml
├── .env.example
├── ruff.toml / .hadolint.yaml
└── .github/workflows/ci.yml
```

### API Gateway

Todo el tráfico externo entra por un **API Gateway NGINX** (`api-gateway`), el **único contenedor que publica un puerto** (`8080`). Los microservicios y las bases de datos quedan en redes internas.

```
Cliente ──► api-gateway :8080 ──┬─► catalog-service ──► sqlserver-catalog
                                └─► booking-service ──► sqlserver-booking
                                         └──────► catalog-service (llamada interna, sin gateway)
```

| Ruta en el gateway | Destino |
|---|---|
| `/api/v1/atracciones`, `/api/v1/temporadas`, `/api/v1/precios` | `catalog-service` |
| `/api/v1/reservas`, `/api/v1/disponibilidad`, `/api/v1/estadisticas/...` | `booking-service` |
| `/catalog/...` (p. ej. `/catalog/docs`) | `catalog-service` sin el prefijo |
| `/booking/...` (p. ej. `/booking/docs`) | `booking-service` sin el prefijo |
| `/health` | Salud del propio gateway |
| Cualquier otra | `404 {"error": "RUTA_NO_ENCONTRADA"}` |

Responsabilidades del gateway:
- **Enrutado** por ruta hacia cada microservicio (los clientes no conocen sus direcciones internas).
- **Rate limiting**: 20 peticiones/s por IP con ráfagas de 40; al superarlo, `429` en JSON.
- **Trazabilidad**: genera una cabecera `X-Request-ID` que se reenvía al servicio y se devuelve al cliente.
- **Seguridad**: oculta la versión de NGINX y añade `X-Content-Type-Options`, `X-Frame-Options` y `Referrer-Policy`.
- **Errores uniformes**: si un servicio no responde, devuelve `503 {"error": "SERVICIO_NO_DISPONIBLE"}` con el mismo formato que la API.
- Resuelve los nombres de los servicios con el DNS interno de Docker en tiempo de ejecución, así que tolera reinicios de los contenedores.

La llamada `booking-service → catalog-service` es tráfico interno (*east-west*) y va directa por la red `services`, sin pasar por el gateway. Cada servicio recibe `ROOT_PATH` (`/catalog`, `/booking`) para que su Swagger funcione detrás del prefijo.

### Dockerfiles de producción

Los microservicios usan el mismo patrón de **tres etapas**:

| Etapa | Contenido | Llega a la imagen final |
|---|---|---|
| `builder` | `venv` con las dependencias de `requirements.txt` | Solo `/opt/venv` |
| `msrepo` | `curl` + `gnupg` para descargar la clave del repositorio de Microsoft | Solo el fichero de clave |
| `runtime` | Python + driver ODBC 18 + venv + código | ✔ |

- **Imagen base `python:3.12-slim-bookworm`**: la variante *slim* elimina compiladores y documentación. Se descarta Alpine porque `pyodbc` y el driver **ODBC 18 de Microsoft** (necesario para Azure SQL) solo existen para glibc; con musl habría que compilar y el driver no está soportado. Se fija Debian 12 (*bookworm*) por estar soportado por el repositorio de Microsoft.
- **Mínimo privilegio**: usuario `app` (UID 10001) de sistema, sin shell ni *home*; `USER 10001:10001`. El código pertenece a `root`, de modo que el proceso no puede modificarlo (**inmutabilidad**). En compose, además, `read_only: true`, `cap_drop: ALL` y `no-new-privileges`.
- **Caché de capas**: se copia `requirements.txt` antes que el código; cambiar el código no reinstala dependencias. `.dockerignore` deja fuera tests, cachés y secretos.
- **Puerto** `8000` expuesto y `HEALTHCHECK` contra `GET /health` usando el propio Python (no se instala `curl` en runtime).

El **API Gateway** (`gateway/Dockerfile`) usa dos etapas sobre `nginxinc/nginx-unprivileged:1.27-alpine`, imagen oficial de NGINX que ya se ejecuta sin root (UID 101) en un puerto no privilegiado (`8080`); Alpine basta porque solo contiene NGINX (~20 MB). La etapa `validate` ejecuta `nginx -t`, de modo que una configuración inválida rompe la construcción (y el CI) en lugar de fallar al arrancar; la etapa `runtime` copia solo la configuración validada.

### Entorno local (un único comando)

```bash
cp .env.example .env          # y cambia las contraseñas de ejemplo
docker compose up -d --build
```

Cada microservicio tiene **su propio contenedor de SQL Server** (*database-per-service* con aislamiento físico): un servicio no puede ver ni alcanzar por red la base de datos del otro, y la caída de una instancia no afecta a la otra.

| Contenedor | Función | Volumen | Redes |
|---|---|---|---|
| `sqlserver-catalog` | SQL Server 2022 con `catalog_db` (mismo motor que Azure SQL: paridad dev/prod) | `rutaticket-sqlserver-catalog-data` | `catalog-data` |
| `db-init-catalog` | Tarea única e idempotente: crea `catalog_db` y el login `catalog_app` | — | `catalog-data` |
| `sqlserver-booking` | SQL Server 2022 con `booking_db` | `rutaticket-sqlserver-booking-data` | `booking-data` |
| `db-init-booking` | Tarea única e idempotente: crea `booking_db` y el login `booking_app` | — | `booking-data` |
| `catalog-service` | API de catálogo (sin puerto publicado) | — | `services`, `catalog-data` |
| `booking-service` | API de reservas (sin puerto publicado) | — | `services`, `booking-data` |
| `api-gateway` | Punto de entrada: http://localhost:8080 · Swagger en `/catalog/docs` y `/booking/docs` | — | `edge`, `services` |

Los dos `db-init-*` ejecutan el mismo script `db/init/init-db.sql`, al que se pasan con `sqlcmd -v` el nombre de la BD, el login y su contraseña. Los logins de aplicación solo tienen `db_datareader`, `db_datawriter` y `db_ddladmin` sobre su BD (no son administradores).

- **Redes**: `edge` es la única conectada al host y solo la usa el gateway; `services` (interna) une gateway y microservicios (y lleva `booking → catalog`); `catalog-data` y `booking-data` (internas) aíslan cada base de datos con su servicio. Ni los microservicios ni las bases de datos publican puertos.
- **Persistencia**: un volumen gestionado por base de datos; los datos se conservan con `docker compose down` / `up`. Para borrarlos: `docker compose down -v`.
- **Orden de arranque** (las dos bases de datos arrancan en paralelo):
  - `sqlserver-catalog` (healthy) → `db-init-catalog` (completed) → `catalog-service` (healthy)
  - `sqlserver-booking` (healthy) → `db-init-booking` (completed) → `booking-service` (espera también a `catalog-service`)
  - `api-gateway` arranca cuando ambos microservicios están *healthy*
- **Memoria**: cada instancia se limita con `MSSQL_MEMORY_LIMIT_MB` (1536 MB por defecto en `.env.example`). Con dos instancias, asigna al menos 5–6 GB a Docker/WSL.
- En Azure (siguiente hito) cada servicio conserva su propia base de datos (`catalog_db`, `booking_db`) en Azure SQL serverless.
- En Mac con Apple Silicon, SQL Server se ejecuta emulado (`platform: linux/amd64`); activa Rosetta en Docker Desktop.

Para probar el clúster:

```bash
pip install -r tests/e2e/requirements.txt
pytest tests/e2e -v
```

### Pruebas

| Tipo | Dónde | Qué valida |
|---|---|---|
| Unitarias | `services/*/tests/unit` | RN-01 a RN-05 y estadísticas como funciones puras |
| Integración (servicio) | `services/*/tests/integration` | API HTTP + SQLAlchemy sobre SQLite; en booking, catálogo simulado y reloj fijo |
| Integración (sistema) | `tests/e2e` | cliente → api-gateway → booking → catalog → sus dos SQL Server reales levantados con compose; además, enrutado, cabeceras y errores del gateway |

```bash
cd services/catalog-service
pip install -r requirements-dev.txt
pytest
```

### Integración continua (`.github/workflows/ci.yml`)

Se ejecuta en cada `push` y `pull_request` a `main` (y en tags `vX.Y.Z`):

1. **lint** — `ruff check` + `ruff format --check`, **hadolint** sobre los tres Dockerfiles y `docker compose config`.
2. **test** — pruebas unitarias y de integración de cada servicio (matriz) con cobertura.
3. **build** — construye las tres imágenes con caché de GitHub Actions y las guarda como artefacto.
4. **e2e** — carga esas imágenes, levanta el compose completo (gateway + dos instancias de SQL Server) y ejecuta `tests/e2e` contra el gateway.
5. **publish** — solo en `push` a `main` o en tags `vX.Y.Z` (nunca desde un *pull request*): publica **la misma imagen que se ha probado** en GHCR:
   - `ghcr.io/leonelljcugr/rutaticket-catalog-service`
   - `ghcr.io/leonelljcugr/rutaticket-booking-service`
   - `ghcr.io/leonelljcugr/rutaticket-api-gateway`

   Etiquetas: `sha-<commit>` siempre, `latest` en `main`, y `X.Y.Z` / `X.Y` al publicar un tag `vX.Y.Z`.

Para usar las imágenes publicadas en lugar de construirlas:

```bash
IMAGE_PREFIX=ghcr.io/leonelljcugr/rutaticket IMAGE_TAG=latest docker compose up -d --no-build
```

### Flujo de trabajo con ramas

Se trabaja con ramas por tipo de cambio y commits semánticos. Ningún cambio llega a `main` sin *pull request* y sin el CI en verde.

| Rama | Uso | Prefijo de los commits |
|---|---|---|
| `main` | Versión estable y entregable. Única rama que publica imágenes en GHCR. | — |
| `feat` | Nuevas funcionalidades | `feat(<servicio>):`, `ci:` |
| `fix` | Corrección de errores | `fix(<servicio>):` |
| `refactor` | Mejoras internas sin cambiar el comportamiento | `refactor(<servicio>):` |
| `docs` | Documentación | `docs:` |

En el Hito 2, `feat` contiene los commits agrupados por servicio, enlazados con su historia de usuario:

| Commit | Contenido | Issue |
|---|---|---|
| `feat(catalog-service)` | Código y Dockerfile del catálogo (CU-01, CU-02, CU-03) | #2 |
| `test(catalog-service)` | Pruebas unitarias y de integración del catálogo | #2 |
| `feat(booking-service)` | Código y Dockerfile de reservas (CU-04 a CU-07) | #3 |
| `test(booking-service)` | Pruebas unitarias y de integración de reservas | #3 |
| `feat(api-gateway)` | API Gateway NGINX y su Dockerfile | #4 |
| `feat(infra)` | `compose.yaml`, bases de datos y `.env.example` | #4 |
| `test(e2e)` | Pruebas del sistema completo a través del gateway | #4 |
| `ci` | Workflow de GitHub Actions y configuración de linters | #4 |
| `refactor` | Mejora de la redacción de los comentarios | #4 |
| `fix(docker)` | Imagen base con versión explícita en cada `FROM` (hadolint DL3006) | #4 |

### Evidencias

Las capturas de las pruebas del Hito 2 (contenedores en ejecución, Swagger a través del API Gateway, reglas de negocio, tests, CI, imágenes publicadas en GHCR y release `v0.2.0`) están recogidas en este documento:

- [Evidencias del Hito 2 (archivo PDF en Google Drive)](https://drive.google.com/file/d/1RlEHt-9yENhLUPrRDFIwGP44rWWtwOtw/view?usp=sharing)