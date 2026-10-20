# Rola pliku: Endpointy kont: rejestracja, logowanie, wylogowanie i /auth/me. Jedyny router dostępny bez
# sesji; ustawia i kasuje ciasteczko HttpOnly z tokenem sesji.

import ipaddress
import logging

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.api.deps import CurrentUserDep, SessionDep, SettingsDep
from app.core.config import Settings
from app.schemas.auth import LoginRequest, MeResponse, RegisterRequest, UserRead, WorkspaceRead
from app.services.auth.service import AuthError, AuthService, CurrentUser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])
_proxy_warning_logged = False

ERROR_STATUS = {
    "email_taken": status.HTTP_409_CONFLICT,
    "invalid_credentials": status.HTTP_401_UNAUTHORIZED,
    "too_many_attempts": status.HTTP_429_TOO_MANY_REQUESTS,
    "too_many_registrations": status.HTTP_429_TOO_MANY_REQUESTS,
    "no_workspace": status.HTTP_403_FORBIDDEN,
}


def _error(exc: AuthError) -> HTTPException:
    return HTTPException(ERROR_STATUS.get(exc.code, status.HTTP_400_BAD_REQUEST), detail={"code": exc.code})


# Za reverse proxy prawdziwe IP daje uvicorn --proxy-headers (docker-compose.prod.yml).
def _client_ip(request: Request, settings: Settings) -> str | None:
    ip = request.client.host if request.client else None
    if ip and settings.cookie_secure:
        _warn_if_private(ip)
    return ip


# W prod (COOKIE_SECURE=true) adres prywatny zwykle oznacza, że reverse proxy nie przekazuje
# X-Forwarded-For: wszyscy dzielą wtedy jedno IP, a limity per IP stają się globalne. Raz na proces.
def _warn_if_private(ip: str) -> None:
    global _proxy_warning_logged
    if _proxy_warning_logged:
        return
    try:
        private = ipaddress.ip_address(ip).is_private
    except ValueError:
        return
    if private:
        _proxy_warning_logged = True
        logger.warning(
            "Żądanie logowania/rejestracji z prywatnego IP %s przy COOKIE_SECURE=true. Sprawdź, czy reverse "
            "proxy ustawia X-Forwarded-For i czy FORWARDED_ALLOW_IPS mu ufa; inaczej limity per IP są wspólne "
            "dla wszystkich użytkowników.", ip,
        )


def _set_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        settings.session_cookie_name, token, max_age=settings.session_ttl_days * 86400, path="/",
        domain=settings.cookie_domain or None, secure=settings.cookie_secure, httponly=True, samesite="lax",
    )


def _me(current: CurrentUser) -> MeResponse:
    return MeResponse(
        user=UserRead(id=current.user_id, email=current.email),
        workspace=WorkspaceRead(id=current.workspace_id, name=current.workspace_name, role=current.role),
    )


async def _login(service: AuthService, request: Request, response: Response, settings: Settings,
                 payload: LoginRequest) -> MeResponse:
    try:
        token = await service.login(payload.email, payload.password, ip=_client_ip(request, settings),
                                    user_agent=request.headers.get("user-agent"))
    except AuthError as exc:
        raise _error(exc) from exc
    _set_cookie(response, settings, token)
    current = await service.resolve(token)
    assert current is not None
    return _me(current)


# Rejestracja od razu loguje: tworzy sesję tak samo jak /auth/login.
@router.post("/register", response_model=MeResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, request: Request, response: Response, session: SessionDep,
                   settings: SettingsDep) -> MeResponse:
    if not settings.allow_registration:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail={"code": "registration_disabled"})
    service = AuthService(session, settings)
    try:
        await service.register(payload.email, payload.password, ip=_client_ip(request, settings))
    except AuthError as exc:
        raise _error(exc) from exc
    return await _login(service, request, response, settings, payload)


@router.post("/login", response_model=MeResponse)
async def login(payload: LoginRequest, request: Request, response: Response, session: SessionDep,
                settings: SettingsDep) -> MeResponse:
    return await _login(AuthService(session, settings), request, response, settings, payload)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, session: SessionDep, settings: SettingsDep) -> Response:
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        await AuthService(session, settings).logout(token)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(settings.session_cookie_name, path="/", domain=settings.cookie_domain or None,
                           secure=settings.cookie_secure, httponly=True, samesite="lax")
    return response


@router.get("/me", response_model=MeResponse)
async def me(current: CurrentUserDep) -> MeResponse:
    return _me(current)
