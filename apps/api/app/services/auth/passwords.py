# Rola pliku: Haszowanie i weryfikacja haseł algorytmem Argon2id (argon2-cffi).

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()
# Hash do porównania, gdy konta nie ma: odpowiedź trwa tyle samo, więc czas nie zdradza istnienia emaila.
_DUMMY_HASH = _hasher.hash("content-engine-dummy-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)
