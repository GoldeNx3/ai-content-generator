# Rola pliku: Komenda operatora ustawiająca miesięczny budżet AI workspace'u (USD). Właściciel workspace'u
# nie może zmienić go sam. `--default` przywraca wartość DEFAULT_MONTHLY_BUDGET_USD z .env.
# Użycie: python -m app.jobs.set_budget --workspace ID (--usd 25 | --default)

import argparse
import asyncio
import sys
from decimal import Decimal, InvalidOperation

from app.core.db import SessionLocal
from app.jobs.workspace_arg import WorkspaceNotFound, resolve_workspace
from app.models import Workspace


async def set_budget(workspace_id: int, usd: Decimal | None) -> str:
    async with SessionLocal() as session:
        workspace = await session.get(Workspace, await resolve_workspace(session, workspace_id))
        workspace.monthly_budget_usd = usd
        await session.commit()
        value = "domyślny (DEFAULT_MONTHLY_BUDGET_USD)" if usd is None else f"{usd} USD / miesiąc"
        return f"Workspace {workspace.id} ({workspace.name}): budżet {value}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Miesięczny budżet AI workspace'u")
    parser.add_argument("--workspace", type=int, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--usd", help="kwota w USD (0 = blokada płatnych zadań)")
    group.add_argument("--default", action="store_true", help="użyj DEFAULT_MONTHLY_BUDGET_USD")
    args = parser.parse_args()
    try:
        usd = None if args.default else Decimal(args.usd)
        if usd is not None and (usd < 0 or usd >= Decimal("100000000")):
            raise InvalidOperation
    except InvalidOperation:
        sys.exit("Podaj kwotę >= 0, np. --usd 25")
    try:
        print(asyncio.run(set_budget(args.workspace, usd)))
    except WorkspaceNotFound as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
