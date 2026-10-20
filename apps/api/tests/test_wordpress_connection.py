# Rola pliku: Testy połączenia WordPress per workspace: ręczne połączenie (test przez Bridge, szyfrowanie
# hasła), autoryzacja aplikacji przez ekran WP (state, workspace), zmiana strony, uprawnienia ownera,
# ochrona SSRF i użycie połączenia workspace'u przez publikację.

import base64
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.models import WordPressConnection, WordPressPublication
from app.enums import WorkspaceRole
from app.services.auth.service import CurrentUser
from app.services.wordpress.client import WordPressClient

GOOD = ("editor", "good pass 1234")


class FakeSite:
    """Minimalny WordPress z Content Engine Bridge: indeks REST, users/me, posts, capabilities."""

    def __init__(self, app_passwords=True):
        self.app_passwords = app_passwords
        self.hosts = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.hosts.append(request.url.host)
        path = request.url.path
        if path.endswith("/wp-json/"):
            auth = {"application-passwords": {"endpoints": {
                "authorization": "https://wp.example/blog/wp-admin/authorize-application.php"}}} if self.app_passwords else {}
            return httpx.Response(200, json={"name": "Blog", "authentication": auth})
        header = request.headers.get("authorization", "")
        if header != "Basic " + base64.b64encode(":".join(GOOD).encode()).decode():
            return httpx.Response(401, json={"code": "rest_not_logged_in"})
        if path.endswith("/users/me"):
            return httpx.Response(200, json={"id": 5, "name": "Ed Itor"})
        if path.endswith("/wp/v2/posts"):
            return httpx.Response(200, json=[])
        if path.endswith("/content-engine/v1/capabilities"):
            return httpx.Response(200, json={"seo_plugin": "rankmath", "can_publish": True, "timezone": "UTC"})
        return httpx.Response(404, json={"code": "rest_no_route"})


@pytest.fixture
def site(monkeypatch):
    fake = FakeSite()
    monkeypatch.setattr(get_settings(), "secrets_key", get_settings().secrets_key or Fernet.generate_key().decode())
    original = WordPressClient.__init__

    def init(self, settings, http=None):
        original(self, settings, http or httpx.AsyncClient(transport=httpx.MockTransport(fake.handle)))
    monkeypatch.setattr(WordPressClient, "__init__", init)
    return fake


def manual(**overrides):
    return {"site_url": "https://WP.example/blog/", "username": GOOD[0], "app_password": GOOD[1], **overrides}


async def test_manual_connect_verifies_bridge_and_encrypts_password(client, session, site):
    response = await client.post("/api/wordpress/connection", json=manual())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["site_url"] == "https://wp.example/blog"
    assert body["seo_plugin"] == "rankmath" and body["can_publish"] and body["wp_user_name"] == "Ed Itor"
    assert "app_password" not in response.text and GOOD[1] not in response.text
    stored = await session.scalar(select(WordPressConnection).where(WordPressConnection.workspace_id == 1))
    assert GOOD[1] not in stored.app_password_encrypted
    assert (await client.get("/api/wordpress/connection")).json()["username"] == GOOD[0]
    assert (await client.post("/api/wordpress/connection/test")).json()["last_error"] is None


async def test_wrong_password_is_not_saved(client, session, site):
    response = await client.post("/api/wordpress/connection", json=manual(app_password="wrong"))
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "wordpress_http_401"
    assert await session.scalar(select(WordPressConnection)) is None


async def test_invalid_url_rejected(client, site):
    for url in ("ftp://wp.example", "https://user:pass@wp.example", "https://wp.example/?a=1", ""):
        assert (await client.post("/api/wordpress/connection", json=manual(site_url=url))).status_code == 422


async def test_authorize_flow_uses_saved_site_and_validates_state(client, session, site):
    start = await client.post("/api/wordpress/connection/authorize", json={"site_url": "https://wp.example/blog"})
    assert start.status_code == 200, start.text
    url = urlsplit(start.json()["authorize_url"])
    assert url.path.endswith("/wp-admin/authorize-application.php")
    params = {key: values[0] for key, values in parse_qs(url.query).items()}
    assert params["app_name"] == "Content Engine"
    success = urlsplit(params["success_url"])
    assert success.path == "/settings/wordpress/callback"
    state = parse_qs(success.query)["state"][0]

    bad = await client.post("/api/wordpress/connection/authorize/complete",
                            json={"state": "x" * 40, "user_login": GOOD[0], "password": GOOD[1]})
    assert bad.status_code == 400 and bad.json()["detail"]["code"] == "wordpress_auth_state_invalid"

    done = await client.post("/api/wordpress/connection/authorize/complete",
                             json={"state": state, "user_login": GOOD[0], "password": GOOD[1]})
    assert done.status_code == 200, done.text
    assert done.json()["site_url"] == "https://wp.example/blog"
    # State jest jednorazowy.
    again = await client.post("/api/wordpress/connection/authorize/complete",
                              json={"state": state, "user_login": GOOD[0], "password": GOOD[1]})
    assert again.status_code == 400


async def test_authorize_state_from_other_workspace_is_rejected(client, site):
    start = await client.post("/api/wordpress/connection/authorize", json={"site_url": "https://wp.example/blog"})
    success = parse_qs(urlsplit(start.json()["authorize_url"]).query)["success_url"][0]
    state = parse_qs(urlsplit(success).query)["state"][0]
    client._transport.app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=1, email="b@example.com", workspace_id=2, workspace_name="obcy", role=WorkspaceRole.OWNER)
    response = await client.post("/api/wordpress/connection/authorize/complete",
                                 json={"state": state, "user_login": GOOD[0], "password": GOOD[1]})
    assert response.status_code == 400


async def test_site_without_app_passwords_is_reported(client, site):
    site.app_passwords = False
    response = await client.post("/api/wordpress/connection/authorize", json={"site_url": "https://wp.example/blog"})
    assert response.json()["detail"]["code"] == "wordpress_app_passwords_unavailable"


async def test_member_cannot_change_connection(client, site):
    client._transport.app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=1, email="m@example.com", workspace_id=1, workspace_name="test", role=WorkspaceRole.MEMBER)
    assert (await client.post("/api/wordpress/connection", json=manual())).status_code == 403
    assert (await client.delete("/api/wordpress/connection")).status_code == 403


async def test_site_change_requires_confirmation_and_unlinks_publications(client, session, site):
    from tests.test_qa_api import article_fixture
    await client.post("/api/wordpress/connection", json=manual())
    connection = await session.scalar(select(WordPressConnection))
    old_instance = connection.instance_id
    article, _ = await article_fixture(session)
    session.add(WordPressPublication(candidate_id=article.candidate_id, article_version_id=article.id,
                                     wordpress_post_id=81, wordpress_instance_id=old_instance,
                                     status="draft_created", wp_status="draft", profile={}, warnings=[]))
    await session.commit()
    other = manual(site_url="https://other.example")
    conflict = await client.post("/api/wordpress/connection", json=other)
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "wordpress_site_change_requires_confirmation"
    assert (await client.post("/api/wordpress/connection", json={**other, "confirm_site_change": True})).status_code == 200
    session.expire_all()
    publication = await session.scalar(select(WordPressPublication))
    assert publication.wordpress_post_id is None and publication.status == "not_sent"
    assert (await session.scalar(select(WordPressConnection))).instance_id != old_instance


async def test_private_addresses_blocked_unless_allowed(client, monkeypatch):
    # Bez fałszywego transportu: prawdziwy klient z PublicHTTPTransport odrzuca adres w sieci wewnętrznej.
    monkeypatch.setattr(get_settings(), "wordpress_allow_private_urls", False)
    response = await client.post("/api/wordpress/connection/authorize", json={"site_url": "http://127.0.0.1:9"})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "wordpress_connection"


async def test_disconnect_and_publish_without_connection(client, session, site):
    await client.post("/api/wordpress/connection", json=manual())
    assert (await client.delete("/api/wordpress/connection")).status_code == 204
    assert (await client.get("/api/wordpress/connection")).json() is None
    from tests.test_qa_api import article_fixture
    article, _ = await article_fixture(session)
    response = await client.post(f"/api/article-versions/{article.id}/wordpress", json={"status": "draft"})
    assert response.status_code == 503
    assert response.json()["detail"] == "wordpress_not_configured"
