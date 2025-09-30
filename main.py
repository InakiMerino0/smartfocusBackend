from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import get_db
from sqlalchemy import text
from routers import v1_auth, v1_events, v1_nl, v1_subjects, v1_users

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

@app.get("/verificar-tabla-usuario")
def verificar_tabla_usuario(db: Session = Depends(get_db)):
    try:
        resultado = db.execute(text("SELECT * FROM USUARIO LIMIT 5"))
        filas = resultado.fetchall()
        return {"ok": True, "filas": [dict(row._mapping) for row in filas]}
    except Exception as e:
        import traceback
        print("❌ Error al consultar tabla USUARIO:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al consultar tabla USUARIO: {str(e)}")




for route in app.routes:
    print(f"{route.path} → {route.methods}")

# Prueba de conexión para asegurar visibilidad temprana de errores de base
try:
    db = next(get_db())
    db.execute(text("SELECT 1"))
    print("✅ Conexión a la base de datos verificada con éxito.")
except Exception as e:
    print("❌ Error de conexión a la base de datos:", str(e))
finally:
    db.close()

for route in app.routes:
    print(f"{route.path} → {route.methods}")