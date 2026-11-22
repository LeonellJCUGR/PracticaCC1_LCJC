# syntax=docker/dockerfile:1
#
# api-gateway - imagen de producción multietapa (NGINX como API Gateway).
#
# Imagen base: nginxinc/nginx-unprivileged:1.27-alpine
#  - Imagen oficial de NGINX preparada para ejecutarse SIN root (usuario nginx, UID 101)
#    y escuchando en un puerto no privilegiado (8080).
#  - Variante Alpine (~20 MB): el gateway no necesita glibc ni Python, solo NGINX.

ARG NGINX_IMAGE=nginxinc/nginx-unprivileged:1.27-alpine

# ---------- Etapa 1: validación de la configuración ----------
# Si gateway.conf tiene un error de sintaxis, la construcción de la imagen falla aquí
# (y por tanto el CI), en lugar de fallar al arrancar el contenedor.
FROM ${NGINX_IMAGE} AS validate
COPY nginx/gateway.conf /etc/nginx/conf.d/default.conf
RUN nginx -t

# ---------- Etapa 2: imagen final de ejecución ----------
FROM ${NGINX_IMAGE} AS runtime

LABEL org.opencontainers.image.title="rutaticket-api-gateway" \
      org.opencontainers.image.description="RutaTicket: API Gateway (NGINX) que enruta hacia catalog-service y booking-service" \
      org.opencontainers.image.source="https://github.com/LeonellJCUGR/PracticaCC1_LCJC"

# Solo se copia la configuración ya validada.
COPY --from=validate /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf

# La imagen base ya define el usuario no root; se declara explícitamente (UID 101 = nginx).
USER 101

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD ["wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/health"]

CMD ["nginx", "-g", "daemon off;"]
