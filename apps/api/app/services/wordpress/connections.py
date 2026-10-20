# Rola pliku: Połączenie WordPress per workspace: zapis (hasło aplikacji szyfrowane), test przez Bridge,
# autoryzacja aplikacji przez ekran WordPressa (authorize-application.php) i budowa ustawień dla
# WordPressClient/WordPressPublisherService używanych przez API i workera.

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode, urlsplit, urlunsplit
from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.secrets import SecretsKeyMissing, decrypt_secret, encrypt_secret
from app.models import WordPressAuthRequest, WordPressConnection, WordPressPublication
from app.models.candidate import Candidate
from app.services.wordpress.client import WordPressClient
from app.services.wordpress.errors import WordPressError

AUTH_REQUEST_TTL = timedelta(minutes=15)
# Stały identyfikator aplikacji w WP: użytkownik widzi go przy haśle aplikacji w swoim profilu.
APP_ID = "5b0b3f5e-6a8f-4f8e-9a51-6f1d3c2e7c10"
APP_NAME = "Content Engine"


class WordPressConnectionError(Exception):
    def __init__(self, code: str, status: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


def normalize_url(value: str | None, *, required: bool = True) -> str | None:
    if not value or not value.strip():
        if required:
            raise WordPressConnectionError("wordpress_invalid_url", 422)
        return None
    parts = urlsplit(value.strip())
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password \
            or parts.query or parts.fragment:
        raise WordPressConnectionError("wordpress_invalid_url", 422)
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip("/"), "", ""))


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def client_settings(base: Settings, *, site_url: str, api_url: str | None, username: str, password: str,
                    instance_id: str = "", seo_plugin: str = "none", default_status: str = "draft",
                    default_author_id: int | None = None, default_category_id: int | None = None) -> Settings:
    """Ustawienia procesu z nadpisanymi polami wordpress_* jednego połączenia (model_copy, bez walidacji)."""
    return base.model_copy(update={
        "wordpress_url": site_url, "wordpress_api_url": api_url or "", "wordpress_username": username,
        "wordpress_app_password": password, "wordpress_instance_id": instance_id,
        "wordpress_seo_plugin": seo_plugin, "wordpress_default_status": default_status,
        "wordpress_default_author_id": default_author_id, "wordpress_default_category_id": default_category_id,
    })


def connection_settings(base: Settings, connection: WordPressConnection) -> Settings:
    return client_settings(
        base, site_url=connection.site_url, api_url=connection.api_url, username=connection.username,
        password=decrypt_secret(base, connection.app_password_encrypted), instance_id=connection.instance_id,
        seo_plugin=connection.seo_plugin, default_status=connection.default_status,
        default_author_id=connection.default_author_id, default_category_id=connection.default_category_id,
    )


async def get_connection(session: AsyncSession, workspace_id: int) -> WordPressConnection | None:
    return await session.scalar(select(WordPressConnection).where(WordPressConnection.workspace_id == workspace_id))


async def settings_for_workspace(session: AsyncSession, workspace_id: int, base: Settings) -> Settings:
    """Ustawienia WordPress workspace'u; brak połączenia -> wordpress_not_configured (jak dawniej puste .env)."""
    connection = await get_connection(session, workspace_id)
    if connection is None:
        raise WordPressError("wordpress_not_configured")
    try:
        return connection_settings(base, connection)
    except SecretsKeyMissing:
        raise WordPressError("wordpress_not_configured") from None


async def settings_for_candidate(session: AsyncSession, candidate_id: int, base: Settings) -> Settings:
    workspace_id = await session.scalar(select(Candidate.workspace_id).where(Candidate.id == candidate_id))
    return await settings_for_workspace(session, workspace_id, base)


async def probe(settings: Settings) -> dict:
    """Test połączenia: użytkownik, dostęp do wpisów i wymagany plugin Content Engine Bridge."""
    client = WordPressClient(settings)
    try:
        return await client.test_connection()
    finally:
        await client.close()


class ConnectionService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def connect(self, workspace_id: int, *, site_url: str, api_url: str | None, username: str,
                      password: str, confirm_site_change: bool = False) -> WordPressConnection:
        site_url = normalize_url(site_url)
        api_url = normalize_url(api_url, required=False)
        username, password = username.strip(), password.strip()
        if not username or not password:
            raise WordPressConnectionError("wordpress_not_configured", 422)
        existing = await get_connection(self.session, workspace_id)
        site_changed = existing is not None and existing.site_url != site_url
        if site_changed and not confirm_site_change and await self._linked_publications(workspace_id, existing.instance_id):
            # Opublikowane posty żyją na starej stronie; po zmianie artykuły trafią na nową jako nowe drafty.
            raise WordPressConnectionError("wordpress_site_change_requires_confirmation", 409)
        try:
            result = await probe(client_settings(self.settings, site_url=site_url, api_url=api_url,
                                                 username=username, password=password))
        except WordPressError as exc:
            raise WordPressConnectionError(exc.code, 422) from None
        caps = result.get("capabilities") or {}
        seo_plugin = caps.get("seo_plugin") if caps.get("seo_plugin") in ("yoast", "rankmath", "none") else "none"
        try:
            encrypted = encrypt_secret(self.settings, password)
        except SecretsKeyMissing:
            raise WordPressConnectionError("secrets_key_missing", 503) from None
        connection = existing or WordPressConnection(workspace_id=workspace_id, instance_id=f"ce-{uuid4().hex}")
        if site_changed:
            await self._unlink_publications(workspace_id, existing.instance_id)
            connection.instance_id = f"ce-{uuid4().hex}"
        connection.site_url, connection.api_url, connection.username = site_url, api_url, username
        connection.app_password_encrypted = encrypted
        connection.seo_plugin = seo_plugin
        connection.wp_user_id = result.get("user_id")
        connection.wp_user_name = result.get("user_name")
        connection.can_publish = bool(caps.get("can_publish"))
        connection.last_checked_at, connection.last_error = datetime.now(UTC), None
        self.session.add(connection)
        await self.session.commit()
        return connection

    async def test(self, workspace_id: int) -> WordPressConnection:
        connection = await get_connection(self.session, workspace_id)
        if connection is None:
            raise WordPressConnectionError("wordpress_not_configured", 404)
        try:
            result = await probe(connection_settings(self.settings, connection))
            caps = result.get("capabilities") or {}
            connection.last_error = None
            connection.can_publish = bool(caps.get("can_publish"))
            if caps.get("seo_plugin") in ("yoast", "rankmath", "none"):
                connection.seo_plugin = caps["seo_plugin"]
        except WordPressError as exc:
            connection.last_error = exc.code
        except SecretsKeyMissing:
            connection.last_error = "secrets_key_missing"
        connection.last_checked_at = datetime.now(UTC)
        await self.session.commit()
        return connection

    async def update_defaults(self, workspace_id: int, values: dict) -> WordPressConnection:
        connection = await get_connection(self.session, workspace_id)
        if connection is None:
            raise WordPressConnectionError("wordpress_not_configured", 404)
        for key in ("default_status", "default_author_id", "default_category_id"):
            if key in values:
                setattr(connection, key, values[key])
        await self.session.commit()
        return connection

    async def disconnect(self, workspace_id: int) -> None:
        # Hasło aplikacji w WP pozostaje do odwołania w profilu użytkownika (Użytkownicy → Profil).
        await self.session.execute(delete(WordPressConnection).where(WordPressConnection.workspace_id == workspace_id))
        await self.session.commit()

    # --- Autoryzacja aplikacji przez ekran WordPressa ---

    async def start_authorization(self, workspace_id: int, user_id: int, *, site_url: str,
                                  api_url: str | None) -> str:
        site_url = normalize_url(site_url)
        api_url = normalize_url(api_url, required=False)
        endpoint = await self._authorize_endpoint(site_url, api_url)
        state = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        await self.session.execute(delete(WordPressAuthRequest).where(WordPressAuthRequest.expires_at < now))
        self.session.add(WordPressAuthRequest(state_hash=_hash(state), workspace_id=workspace_id, user_id=user_id,
                                              site_url=site_url, api_url=api_url, expires_at=now + AUTH_REQUEST_TTL))
        await self.session.commit()
        callback = f"{self.settings.web_url}/settings/wordpress/callback"
        params = {
            "app_name": APP_NAME, "app_id": APP_ID,
            # WP dopisuje site_url, user_login i password do success_url; state wraca w niezmienionej postaci.
            "success_url": f"{callback}?{urlencode({'state': state})}",
            "reject_url": f"{callback}?{urlencode({'state': state, 'rejected': '1'})}",
        }
        return f"{endpoint}?{urlencode(params)}"

    async def complete_authorization(self, workspace_id: int, user_id: int, *, state: str, username: str,
                                     password: str, confirm_site_change: bool = False) -> WordPressConnection:
        request = await self.session.scalar(select(WordPressAuthRequest).where(
            WordPressAuthRequest.state_hash == _hash(state), WordPressAuthRequest.expires_at > datetime.now(UTC)))
        # State z innego workspace'u/konta traktujemy jak nieważny: nie da się podpiąć cudzej autoryzacji.
        if request is None or request.workspace_id != workspace_id or request.user_id != user_id:
            raise WordPressConnectionError("wordpress_auth_state_invalid", 400)
        site_url, api_url = request.site_url, request.api_url
        await self.session.delete(request)
        await self.session.commit()
        # Adres strony bierzemy z zapisanego żądania, nie z parametrów powrotu (nie do podmiany w URL).
        return await self.connect(workspace_id, site_url=site_url, api_url=api_url, username=username,
                                  password=password, confirm_site_change=confirm_site_change)

    async def _authorize_endpoint(self, site_url: str, api_url: str | None) -> str:
        # Indeks REST API podaje adres ekranu autoryzacji, gdy hasła aplikacji są włączone (WP 5.6+, HTTPS
        # albo środowisko local).
        client = WordPressClient(client_settings(self.settings, site_url=site_url, api_url=api_url,
                                                 username="", password=""))
        try:
            index = await client.request("GET", "", auth=False)
        except WordPressError as exc:
            raise WordPressConnectionError(exc.code if exc.code != "wordpress_invalid_json" else "wordpress_not_wordpress", 422) from None
        finally:
            await client.close()
        endpoint = (((index or {}).get("authentication") or {}).get("application-passwords") or {}) \
            .get("endpoints", {}).get("authorization")
        if not endpoint:
            raise WordPressConnectionError("wordpress_app_passwords_unavailable", 422)
        return endpoint

    async def _linked_publications(self, workspace_id: int, instance_id: str) -> bool:
        return bool(await self.session.scalar(select(WordPressPublication.id).join(Candidate,
            Candidate.id == WordPressPublication.candidate_id).where(
            Candidate.workspace_id == workspace_id, WordPressPublication.wordpress_instance_id == instance_id,
            WordPressPublication.wordpress_post_id.is_not(None)).limit(1)))

    async def _unlink_publications(self, workspace_id: int, instance_id: str) -> None:
        candidate_ids = select(Candidate.id).where(Candidate.workspace_id == workspace_id)
        await self.session.execute(update(WordPressPublication).where(
            WordPressPublication.candidate_id.in_(candidate_ids),
            WordPressPublication.wordpress_instance_id == instance_id,
        ).values(wordpress_post_id=None, wordpress_instance_id=None, wordpress_url=None, wp_status=None,
                 status="not_sent", last_synced_at=None, last_synced_content_hash=None, media_id=None,
                 media_fingerprint=None, conflict=None, error_code=None))
