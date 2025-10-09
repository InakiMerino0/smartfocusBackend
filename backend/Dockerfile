FROM python:3.11-slim

ARG COMMIT_SHA=unknown
LABEL org.opencontainers.image.source="https://github.com/inakimerino0/smartfocus-backend"
LABEL org.opencontainers.image.revision=$COMMIT_SHA

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Curl para healthcheck interno (si lo usás)
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala deps primero para cachear capas
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copiá SOLO el código del backend (evitás arrastrar .git y basura)
COPY smartfocusBackend ./smartfocusBackend

# Usuario no root
RUN useradd -u 10001 -m appuser
USER 10001:10001

EXPOSE 8000

# Si NO tenés /ready, cambiá a /docs o quita el HEALTHCHECK
HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8000/ready || exit 1

CMD ["uvicorn","smartfocusBackend.main:app","--host","0.0.0.0","--port","8000"]
