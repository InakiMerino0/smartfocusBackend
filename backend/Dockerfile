FROM python:3.11-slim

WORKDIR /app

# deps del sistema (psycopg2 necesita libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copia el código (ajusta si tu módulo no es "smartfocusBackend")
COPY . .

# expone FastAPI por 8000
EXPOSE 8000
CMD ["uvicorn", "smartfocusBackend.main:app", "--host", "0.0.0.0", "--port", "8000"]
