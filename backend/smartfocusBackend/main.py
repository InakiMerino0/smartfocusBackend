from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import get_db
from sqlalchemy import text
from .routers import v1_auth, v1_events, v1_nl, v1_subjects, v1_users

app = FastAPI(
    title="SmartFocus Backend",
    description="Autenticación de usuarios, gestión de eventos y materias con IA",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_auth.router)
app.include_router(v1_events.router)
app.include_router(v1_nl.router)  
app.include_router(v1_subjects.router)
app.include_router(v1_users.router)