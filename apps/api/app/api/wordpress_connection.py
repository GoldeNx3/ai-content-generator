# Rola pliku: Endpointy połączenia WordPress workspace'u: odczyt, autoryzacja aplikacji przez ekran
# WordPressa, ręczne połączenie (login + hasło aplikacji), test, domyślne ustawienia i rozłączenie.
# Zmiany może robić tylko owner workspace'u.

from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import CurrentUserDep, SessionDep, SettingsDep
from app.models.enums import WorkspaceRole
from app.schemas.wordpress_connection import (
    AuthorizeComplete,
    AuthorizeStart,
    AuthorizeStartResponse,
    ConnectionRead,
    DefaultsUpdate,
    ManualConnect,
)
from app.services.auth.service import CurrentUser
from app.services.wordpress.connections import ConnectionService, WordPressConnectionError, get_connection

router = APIRouter(prefix="/wordpress/connection", tags=["wordpress"])


def _owner(current: CurrentUser) -> None:
    if current.role != WorkspaceRole.OWNER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail={"code": "owner_required"})


def _error(exc: WordPressConnectionError) -> HTTPException:
    return HTTPException(exc.status, detail={"code": exc.code})


@router.get("", response_model=ConnectionRead | None)
async def read_connection(session: SessionDep, current: CurrentUserDep):
    return await get_connection(session, current.workspace_id)


@router.post("", response_model=ConnectionRead)
async def connect_manually(body: ManualConnect, session: SessionDep, settings: SettingsDep, current: CurrentUserDep):
    _owner(current)
    try:
        return await ConnectionService(session, settings).connect(
            current.workspace_id, site_url=body.site_url, api_url=body.api_url, username=body.username,
            password=body.app_password, confirm_site_change=body.confirm_site_change)
    except WordPressConnectionError as exc:
        raise _error(exc) from None


@router.post("/authorize", response_model=AuthorizeStartResponse)
async def start_authorization(body: AuthorizeStart, session: SessionDep, settings: SettingsDep,
                              current: CurrentUserDep):
    _owner(current)
    try:
        url = await ConnectionService(session, settings).start_authorization(
            current.workspace_id, current.user_id, site_url=body.site_url, api_url=body.api_url)
    except WordPressConnectionError as exc:
        raise _error(exc) from None
    return AuthorizeStartResponse(authorize_url=url)


@router.post("/authorize/complete", response_model=ConnectionRead)
async def complete_authorization(body: AuthorizeComplete, session: SessionDep, settings: SettingsDep,
                                 current: CurrentUserDep):
    _owner(current)
    try:
        return await ConnectionService(session, settings).complete_authorization(
            current.workspace_id, current.user_id, state=body.state, username=body.user_login,
            password=body.password, confirm_site_change=body.confirm_site_change)
    except WordPressConnectionError as exc:
        raise _error(exc) from None


@router.post("/test", response_model=ConnectionRead)
async def test_connection(session: SessionDep, settings: SettingsDep, current: CurrentUserDep):
    try:
        return await ConnectionService(session, settings).test(current.workspace_id)
    except WordPressConnectionError as exc:
        raise _error(exc) from None


@router.patch("", response_model=ConnectionRead)
async def update_defaults(body: DefaultsUpdate, session: SessionDep, settings: SettingsDep, current: CurrentUserDep):
    _owner(current)
    try:
        return await ConnectionService(session, settings).update_defaults(
            current.workspace_id, body.model_dump(exclude_unset=True))
    except WordPressConnectionError as exc:
        raise _error(exc) from None


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect(session: SessionDep, settings: SettingsDep, current: CurrentUserDep) -> Response:
    _owner(current)
    await ConnectionService(session, settings).disconnect(current.workspace_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
