# Rola pliku: Testy kont: rejestracja, logowanie, limit prób, sesja w ciasteczku, wylogowanie, ochrona
# endpointów (401) i kontrola nagłówka Origin (CSRF).

from datetime import UTC, datetime, timedelta

from sqlalchemy import update

from app.core.config import get_settings
from app.models import UserSession

PASSWORD = "correct horse battery"


async def register(client, email="Jan@Example.com", password=PASSWORD):
    return await client.post("/api/auth/register", json={"email": email, "password": password})


async def test_protected_endpoint_requires_session(anon_client):
    response = await anon_client.get("/api/sources")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "not_authenticated"


async def test_register_logs_in_and_creates_owner_workspace(anon_client):
    response = await register(anon_client)
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "jan@example.com"
    assert body["workspace"]["role"] == "owner"
    assert get_settings().session_cookie_name in response.cookies

    assert (await anon_client.get("/api/auth/me")).json()["user"]["email"] == "jan@example.com"
    assert (await anon_client.get("/api/sources")).status_code == 200


async def test_register_rejects_duplicate_email_and_short_password(anon_client):
    await register(anon_client)
    duplicate = await register(anon_client, email="jan@example.com ")
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "email_taken"
    assert (await register(anon_client, email="ola@example.com", password="short")).status_code == 422


async def test_registration_can_be_disabled(anon_client):
    # Fixture klienta kopiuje ustawienia z get_settings() przy każdym żądaniu, więc zmiana jest widoczna.
    settings = get_settings()
    original = settings.allow_registration
    settings.allow_registration = False
    try:
        response = await register(anon_client)
    finally:
        settings.allow_registration = original
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "registration_disabled"


async def test_login_logout_and_wrong_password(anon_client):
    await register(anon_client)
    anon_client.cookies.clear()

    wrong = await anon_client.post("/api/auth/login", json={"email": "jan@example.com", "password": "nope"})
    assert wrong.status_code == 401
    assert wrong.json()["detail"]["code"] == "invalid_credentials"
    missing = await anon_client.post("/api/auth/login", json={"email": "nikt@example.com", "password": "x"})
    assert missing.status_code == 401

    ok = await anon_client.post("/api/auth/login", json={"email": "JAN@example.com", "password": PASSWORD})
    assert ok.status_code == 200
    assert (await anon_client.get("/api/auth/me")).status_code == 200

    token = anon_client.cookies.get(get_settings().session_cookie_name)
    assert (await anon_client.post("/api/auth/logout")).status_code == 204
    # Unieważniona po stronie bazy: stary token nie działa, nawet gdy klient go nadal wyśle.
    anon_client.cookies.set(get_settings().session_cookie_name, token)
    assert (await anon_client.get("/api/auth/me")).status_code == 401


async def test_login_is_throttled_after_repeated_failures(anon_client):
    await register(anon_client)
    anon_client.cookies.clear()
    for _ in range(get_settings().auth_max_failures_per_email):
        await anon_client.post("/api/auth/login", json={"email": "jan@example.com", "password": "bad"})
    blocked = await anon_client.post("/api/auth/login", json={"email": "jan@example.com", "password": PASSWORD})
    assert blocked.status_code == 429
    assert blocked.json()["detail"]["code"] == "too_many_attempts"


async def test_expired_session_is_rejected(anon_client, session):
    await register(anon_client)
    await session.execute(update(UserSession).values(expires_at=datetime.now(UTC) - timedelta(minutes=1)))
    await session.commit()
    assert (await anon_client.get("/api/auth/me")).status_code == 401


async def test_foreign_origin_cannot_change_state(anon_client):
    response = await anon_client.post("/api/auth/login", headers={"Origin": "https://evil.example"},
                                      json={"email": "jan@example.com", "password": PASSWORD})
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "origin_not_allowed"
    allowed = await register(anon_client)
    assert allowed.status_code == 201


async def test_registration_is_limited_per_ip(anon_client):
    limit = get_settings().auth_max_registrations_per_ip
    # Zajęty email też zużywa limit: inaczej dałoby się sondować istniejące konta bez ograniczeń.
    for index in range(limit):
        anon_client.cookies.clear()
        email = "jan@example.com" if index % 2 else f"user{index}@example.com"
        assert (await register(anon_client, email=email)).status_code in (201, 409)
    blocked = await register(anon_client, email="nowy@example.com")
    assert blocked.status_code == 429
    assert blocked.json()["detail"]["code"] == "too_many_registrations"
    # Limit rejestracji nie blokuje logowania istniejących kont.
    login = await anon_client.post("/api/auth/login", json={"email": "user0@example.com", "password": PASSWORD})
    assert login.status_code == 200


async def test_private_client_ip_in_production_logs_proxy_warning(anon_client, caplog, monkeypatch):
    import app.api.auth as auth_api
    monkeypatch.setattr(auth_api, "_proxy_warning_logged", False)
    settings = get_settings()
    monkeypatch.setattr(settings, "cookie_secure", True)
    # ASGITransport podaje klienta 127.0.0.1, czyli adres prywatny jak bramka Dockera bez proxy headers.
    with caplog.at_level("WARNING", logger="app.api.auth"):
        await anon_client.post("/api/auth/login", json={"email": "jan@example.com", "password": "x"})
        await anon_client.post("/api/auth/login", json={"email": "jan@example.com", "password": "x"})
    warnings = [r for r in caplog.records if "X-Forwarded-For" in r.getMessage()]
    assert len(warnings) == 1


async def test_account_without_password_cannot_log_in_with_password(anon_client, session):
    from app.models import User
    # Konto tylko z Google/Apple (bez hasła) nie może dać się otworzyć żadnym hasłem.
    session.add(User(email="oauth@example.com", password_hash=None, is_active=True))
    await session.commit()
    response = await anon_client.post("/api/auth/login", json={"email": "oauth@example.com", "password": PASSWORD})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_credentials"
