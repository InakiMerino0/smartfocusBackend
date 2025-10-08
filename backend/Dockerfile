# Imagen base estable y liviana
FROM python:3.11-slim

# Optimizaciones de Python + pip sin caché
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Paquetes mínimos para healthcheck y networking
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

# Usuario no-root (UID/GID fijos)
RUN addgroup --system app && adduser --system --ingroup app --uid 10001 app

WORKDIR /app

# Mantener la capa de deps cacheable
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install -r requirements.txt

# Copiar sólo el código de la app
COPY smartfocusBackend ./smartfocusBackend
RUN chown -R app:app /app

USER 10001:10001

EXPOSE 8000

# Healthcheck interno del contenedor (requiere endpoint /ready)
HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8000/ready || exit 1

# Server ASGI
CMD ["uvicorn","smartfocusBackend.main:app","--host","0.0.0.0","--port","8000"]

# (Opcional, mejor performance CPU multi-core)
# CMD ["gunicorn","-k","uvicorn.workers.UvicornWorker","-w","2","-b","0.0.0.0:8000","smartfocusBackend.main:app"]
