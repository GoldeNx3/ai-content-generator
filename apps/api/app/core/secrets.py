# Rola pliku: Szyfrowanie sekretów zapisywanych w bazie (np. Application Password WordPressa) kluczem
# SECRETS_KEY z .env (Fernet: AES-128-CBC + HMAC). Wyciek samej bazy nie ujawnia haseł.

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings


class SecretsKeyMissing(Exception):
    pass


def _fernet(settings: Settings) -> Fernet:
    if not settings.secrets_key:
        raise SecretsKeyMissing("Ustaw SECRETS_KEY w .env (python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\")")
    return Fernet(settings.secrets_key.encode())


def encrypt_secret(settings: Settings, value: str) -> str:
    return _fernet(settings).encrypt(value.encode()).decode()


def decrypt_secret(settings: Settings, token: str) -> str:
    try:
        return _fernet(settings).decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise SecretsKeyMissing("SECRETS_KEY nie pasuje do zaszyfrowanych danych") from exc
