# Rola pliku: Schematy danych logowania i rejestracji oraz odpowiedź /auth/me z użytkownikiem i jego
# aktywnym workspace'em.

import re

from pydantic import BaseModel, Field, field_validator

from app.models.enums import WorkspaceRole

# Celowo prosta walidacja; pełną weryfikację adresu dałoby dopiero potwierdzenie mailem.
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(value: str) -> str:
    return value.strip().lower()


class LoginRequest(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("email")
    @classmethod
    def email_normalized(cls, value: str) -> str:
        return normalize_email(value)


class RegisterRequest(LoginRequest):
    password: str = Field(min_length=10, max_length=1024)

    @field_validator("email")
    @classmethod
    def email_valid(cls, value: str) -> str:
        if not EMAIL_RE.match(value):
            raise ValueError("Niepoprawny adres email")
        return value


class UserRead(BaseModel):
    id: int
    email: str


class WorkspaceRead(BaseModel):
    id: int
    name: str
    role: WorkspaceRole


class MeResponse(BaseModel):
    user: UserRead
    workspace: WorkspaceRead
