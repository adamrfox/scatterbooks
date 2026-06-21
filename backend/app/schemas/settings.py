from typing import Literal

from pydantic import BaseModel

KeySource = Literal["database", "environment", "none"]


class AppSettingsOut(BaseModel):
    google_books_api_key_configured: bool
    google_books_api_key_source: KeySource
    anthropic_api_key_configured: bool
    anthropic_api_key_source: KeySource


class AppSettingsUpdate(BaseModel):
    google_books_api_key: str | None = None
    anthropic_api_key: str | None = None
