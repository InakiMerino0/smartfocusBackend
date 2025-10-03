# utils.py
from __future__ import annotations
from passlib.context import CryptContext

# El primer esquema de la lista es el que se usa para NUEVOS hashes.
# Mantenemos bcrypt_sha256 solo para VERIFICAR hashes antiguos (si existieran).
_pwd = CryptContext(
    schemes=["pbkdf2_sha256", "bcrypt_sha256"],
    deprecated="auto",  # marca como deprecados los que no sean el primero
)

def hash_clave(plain_password: str) -> str:
    """
    Hashea la contraseña con pbkdf2_sha256 (sin límite de 72 bytes).
    Lanza ValueError si la contraseña es vacía o no es str.
    """
    if not isinstance(plain_password, str) or not plain_password:
        raise ValueError("La contraseña no puede estar vacía.")
    return _pwd.hash(plain_password)

def verificar_clave(plain_password: str, stored_hash: str) -> bool:
    """
    Verifica en tiempo constante la contraseña contra el hash almacenado.
    Soporta pbkdf2_sha256 y bcrypt_sha256 (compatibilidad).
    """
    if not stored_hash or not isinstance(plain_password, str) or not plain_password:
        return False
    try:
        return _pwd.verify(plain_password, stored_hash)
    except Exception:
        return False
