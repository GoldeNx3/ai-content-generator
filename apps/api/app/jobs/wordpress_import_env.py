# Rola pliku: Jednorazowe przeniesienie dawnej, globalnej konfiguracji WordPress z .env (WORDPRESS_*) do
# połączenia wybranego workspace'u. Zachowuje WORDPRESS_INSTANCE_ID, więc istniejące publikacje (migracja
# 0011) pozostają powiązane ze swoimi postami. Potem WORDPRESS_* w .env nie są już używane.

import argparse
import asyncio
import sys

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.secrets import SecretsKeyMissing, encrypt_secret
from app.jobs.workspace_arg import WorkspaceNotFound, resolve_workspace, workspace_argument
from app.models import WordPressConnection
from app.services.wordpress.connections import get_connection, normalize_url


async def import_env(workspace_id: int | None) -> str:
    settings = get_settings()
    if not settings.wordpress_url or not settings.wordpress_username or not settings.wordpress_app_password:
        raise SystemExit("Brak WORDPRESS_URL / WORDPRESS_USERNAME / WORDPRESS_APP_PASSWORD w .env")
    async with SessionLocal() as session:
        workspace_id = await resolve_workspace(session, workspace_id)
        if await get_connection(session, workspace_id):
            raise SystemExit(f"Workspace {workspace_id} ma już połączenie WordPress; najpierw je rozłącz w panelu.")
        session.add(WordPressConnection(
            workspace_id=workspace_id, site_url=normalize_url(settings.wordpress_url),
            api_url=normalize_url(settings.wordpress_api_url, required=False), username=settings.wordpress_username,
            app_password_encrypted=encrypt_secret(settings, settings.wordpress_app_password),
            instance_id=settings.wordpress_instance_id, seo_plugin=settings.wordpress_seo_plugin,
            default_status=settings.wordpress_default_status, default_author_id=settings.wordpress_default_author_id,
            default_category_id=settings.wordpress_default_category_id,
        ))
        await session.commit()
    return f"Zaimportowano {settings.wordpress_url} do workspace'u {workspace_id}. Sprawdź połączenie w panelu (Ustawienia)."


def main() -> None:
    parser = argparse.ArgumentParser(description="Import WORDPRESS_* z .env do workspace'u")
    workspace_argument(parser)
    try:
        print(asyncio.run(import_env(parser.parse_args().workspace)))
    except (WorkspaceNotFound, SecretsKeyMissing) as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
