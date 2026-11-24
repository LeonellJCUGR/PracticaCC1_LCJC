# syntax=docker/dockerfile:1
#
# catalog-service - imagen de producción multietapa.
#
# Imagen base: python:3.12-slim-bookworm
#  - "slim" (~45 MB comprimida) frente a la completa (~370 MB): sin compiladores ni docs.
#  - Debian (glibc) y no Alpine (musl): pyodbc y el driver ODBC 18 de Microsoft para
#    SQL Server / Azure SQL solo se distribuyen para glibc y las wheels manylinux funcionan
#    sin compilar. Se fija bookworm (Debian 12) porque es una versión soportada por el
#    repositorio de paquetes de Microsoft.



# ---------- Etapa 1: dependencias Python en un entorno virtual aislado ----------
FROM python:3.12-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

# Solo se copia requirements.txt: esta capa (la más lenta) se reutiliza de la caché
# mientras no cambien las dependencias, aunque cambie el código.
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# ---------- Etapa 2: clave del repositorio de Microsoft (curl/gpg no llegan a runtime) ----------
FROM python:3.12-slim-bookworm AS msrepo

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gnupg \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
       | gpg --dearmor -o /microsoft-prod.gpg \
    && rm -rf /var/lib/apt/lists/*

# ---------- Etapa 3: imagen final de ejecución ----------
FROM python:3.12-slim-bookworm AS runtime

LABEL org.opencontainers.image.title="rutaticket-catalog-service" \
      org.opencontainers.image.description="RutaTicket: catálogo de atractivos y precios por temporada" \
      org.opencontainers.image.source="https://github.com/LeonellJCUGR/PracticaCC1_LCJC"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}"

# Driver ODBC 18 (necesario para pyodbc -> SQL Server / Azure SQL).
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
COPY --from=msrepo /microsoft-prod.gpg /usr/share/keyrings/microsoft-prod.gpg
RUN echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
       > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# Usuario sin privilegios, sin shell de login y sin home.
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /srv
# El código pertenece a root y es de solo lectura para "app": la imagen es inmutable.
COPY app ./app

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
