FROM python:3.11-slim

ARG COMMIT_SHA=unknown
LABEL org.opencontainers.image.revision=$COMMIT_SHA
ENV APP_COMMIT_SHA=$COMMIT_SHA

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 👇 OJO: como el contexto es ./backend, los paths son relativos a esa carpeta
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copiá TODO el código (desde ./backend)
COPY . /app/

# Usuario no root
RUN useradd -u 10001 -m appuser
USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8000/ready || exit 1

CMD ["uvicorn","smartfocusBackend.main:app","--host","0.0.0.0","--port","8000"]
