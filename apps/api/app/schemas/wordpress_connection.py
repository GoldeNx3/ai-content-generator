# Rola pliku: Schematy połączenia WordPress w ustawieniach workspace'u. Hasło aplikacji przyjmujemy
# wyłącznie na wejściu; odpowiedzi nigdy go nie zawierają.

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ConnectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    site_url: str
    api_url: str | None
    username: str
    seo_plugin: str
    default_status: str
    default_author_id: int | None
    default_category_id: int | None
    wp_user_id: int | None
    wp_user_name: str | None
    can_publish: bool
    last_checked_at: datetime | None
    last_error: str | None


class ManualConnect(BaseModel):
    site_url: str = Field(max_length=2048)
    api_url: str | None = Field(default=None, max_length=2048)
    username: str = Field(min_length=1, max_length=200)
    app_password: str = Field(min_length=1, max_length=200)
    confirm_site_change: bool = False


class AuthorizeStart(BaseModel):
    site_url: str = Field(max_length=2048)
    api_url: str | None = Field(default=None, max_length=2048)


class AuthorizeStartResponse(BaseModel):
    authorize_url: str


class AuthorizeComplete(BaseModel):
    state: str = Field(min_length=10, max_length=200)
    user_login: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=200)
    confirm_site_change: bool = False


class DefaultsUpdate(BaseModel):
    default_status: Literal["draft", "future", "publish"] | None = None
    default_author_id: int | None = Field(default=None, gt=0)
    default_category_id: int | None = Field(default=None, gt=0)
