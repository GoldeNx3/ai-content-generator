# Rola pliku: Komenda CLI zakładająca konto (użytkownik + własny workspace) bez publicznej rejestracji.
# Użycie: python -m app.jobs.create_user email@example.com (hasło wczytywane interaktywnie).

import asyncio
import getpass
import sys

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.schemas.auth import RegisterRequest
from app.services.auth.service import AuthError, AuthService


async def create_user(email: str, password: str) -> None:
    payload = RegisterRequest(email=email, password=password)
    async with SessionLocal() as session:
        await AuthService(session, get_settings()).register(payload.email, payload.password)
    print(f"Utworzono konto {payload.email}")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Użycie: python -m app.jobs.create_user EMAIL")
    password = getpass.getpass("Hasło (min. 10 znaków): ")
    if password != getpass.getpass("Powtórz hasło: "):
        sys.exit("Hasła się różnią")
    try:
        asyncio.run(create_user(sys.argv[1], password))
    except AuthError as exc:
        sys.exit(f"Błąd: {exc.code}")
    except ValueError as exc:
        sys.exit(f"Błąd walidacji: {exc}")


if __name__ == "__main__":
    main()
