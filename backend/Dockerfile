# Imagen base estable y liviana
FROM python:3.11-slim

# -------- etiquetas/trazabilidad ----------
ARG COMMIT_SHA=unknown
LABEL org.opencontainers.image.revision=$COMMIT_SHA
ENV APP_COMMIT_SHA=$COMMIT_SHA

# -------- optimizaciones Python/pip ----------
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Dependencias del sistema mínimas (curl para healthcheck)
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

# -------- directorio de la app ----------
WORKDIR /app

# Primero solo requirements para aprovechar caché
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Ahora sí, copiamos TODO el código de la app
# (Asegurate que .dockerignore NO excluya /backend)
COPY backend/ /app/

# Usuario no root
RUN useradd -u 10001 -m appuser
USER 10001:10001

EXPOSE 8000

# Healthcheck interno (requiere endpoint /ready)
HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8000/ready || exit 1

# Server ASGI
CMD ["uvicorn","smartfocusBackend.main:app","--host","0.0.0.0","--port","8000"]
