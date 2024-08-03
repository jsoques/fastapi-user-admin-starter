import bcrypt


# Hash a password using bcrypt
def hash_password(password):
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password=pwd_bytes, salt=salt)
    return hashed_password


# Check if the provided password matches the stored password (hashed)
def verify_password(plain_password, hashed_password) -> bool:
    password_byte_enc = bytes(plain_password.encode("utf-8"))
    try:
        if not isinstance(hashed_password, (bytes, bytearray)):
            hashed_byte_enc = bytes(hashed_password.encode("utf-8"))
            hashed_password = hashed_byte_enc
    except (UnicodeDecodeError, AttributeError):
        pass
    try:
        return bcrypt.checkpw(
            password=password_byte_enc, hashed_password=hashed_password
        )
    except Exception:
        return False
