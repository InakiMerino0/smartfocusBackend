FROM python:3.11-slim

WORKDIR /app

# dependencias del sistema si hicieran falta (opcional)
# RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# copia solo el backend (ajustá si tu estructura es distinta)
COPY smartfocusBackend ./smartfocusBackend

# (opcional) si tenés más módulos, copiarlos aquí
# COPY other_module ./other_module

EXPOSE 8000

# target de uvicorn debe apuntar al paquete real
CMD ["uvicorn", "smartfocusBackend.main:app", "--host", "0.0.0.0", "--port", "8000"]
