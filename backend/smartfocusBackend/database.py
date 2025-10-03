# database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

SQLALCHEMY_DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ── Engine con settings seguros de pool ───────────────────────────────────────
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,    # valida conexiones muertas antes de usarlas
    pool_size=10,          # tamaño base del pool
    max_overflow=20,       # conexiones extra en picos
    pool_recycle=1800,     # recicla conexiones cada 30 min
    future=True,           # API 2.0
    # echo=True,           # habilitar para debug de SQL
)

# ── Session factory ──────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
)

# Instancia db para models SQLAlchemy
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
