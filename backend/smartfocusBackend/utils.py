from passlib.context import CryptContext

_pwd = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

# Genera clave hash para almacenar en la DB con bcrypt
def hash_clave(plain_password: str) -> str:

    if not isinstance(plain_password, str) or not plain_password:
        raise ValueError("La contraseña no puede estar vacía.")
    return _pwd.hash(plain_password)

# Verifica que plain_password coincida con el hash bcrypt almacenado en DB
def verificar_clave(plain_password: str, stored_hash: str) -> bool:
    
    if not stored_hash:
        return False
    try:
        return _pwd.verify(plain_password, stored_hash)
    except Exception:
        return False
