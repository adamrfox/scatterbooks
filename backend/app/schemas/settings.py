from typing import Literal

from pydantic import BaseModel

KeySource = Literal["database", "environment", "none"]


class PublicSettingsOut(BaseModel):
    library_name: str
    anthropic_api_key_configured: bool


class AppSettingsOut(BaseModel):
    library_name: str
    google_books_api_key_configured: bool
    google_books_api_key_source: KeySource
    anthropic_api_key_configured: bool
    anthropic_api_key_source: KeySource


class AppSettingsUpdate(BaseModel):
    library_name: str | None = None
    google_books_api_key: str | None = None
    anthropic_api_key: str | None = None
