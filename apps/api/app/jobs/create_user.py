# Rola pliku: Komenda CLI zakładająca konto bez publicznej rejestracji: nowy użytkownik z własnym
# workspace'em albo (--workspace ID) jako owner istniejącego, np. „Domyślnego” z migracji 0010.
# Użycie: python -m app.jobs.create_user email@example.com [--workspace ID] (hasło wczytywane interaktywnie).

import argparse
import asyncio
import getpass
import sys

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.schemas.auth import RegisterRequest
from app.services.auth.service import AuthError, AuthService


async def create_user(email: str, password: str, workspace_id: int | None = None) -> None:
    payload = RegisterRequest(email=email, password=password)
    async with SessionLocal() as session:
        await AuthService(session, get_settings()).register(payload.email, payload.password,
                                                            workspace_id=workspace_id)
    target = f"workspace {workspace_id}" if workspace_id is not None else "nowy workspace"
    print(f"Utworzono konto {payload.email} ({target})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Załóż konto użytkownika")
    parser.add_argument("email")
    parser.add_argument("--workspace", type=int, default=None, help="dołącz jako owner istniejącego workspace'u")
    args = parser.parse_args()
    password = getpass.getpass("Hasło (min. 10 znaków): ")
    if password != getpass.getpass("Powtórz hasło: "):
        sys.exit("Hasła się różnią")
    try:
        asyncio.run(create_user(args.email, password, args.workspace))
    except AuthError as exc:
        sys.exit(f"Błąd: {exc.code}")
    except ValueError as exc:
        sys.exit(f"Błąd walidacji: {exc}")


if __name__ == "__main__":
    main()
