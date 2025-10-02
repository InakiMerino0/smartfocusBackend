# utils.py
from passlib.context import CryptContext

# Configura bcrypt (incluye salt aleatoria y factor de costo)
_pwd = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

def hash_clave(plain_password: str) -> str:
    """
    Genera un hash bcrypt para almacenar en usuario_password.   
    """
    if not isinstance(plain_password, str) or not plain_password:
        raise ValueError("La contraseña no puede estar vacía.")
    return _pwd.hash(plain_password)

def verificar_clave(plain_password: str, stored_hash: str) -> bool:
    """
    Verifica que plain_password coincida con el hash bcrypt almacenado.
    """
    if not stored_hash:
        return False
    try:
        return _pwd.verify(plain_password, stored_hash)
    except Exception:
        return False
