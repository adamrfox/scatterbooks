from typing import Literal

from pydantic import BaseModel


class AppSettingsOut(BaseModel):
    google_books_api_key_configured: bool
    google_books_api_key_source: Literal["database", "environment", "none"]


class AppSettingsUpdate(BaseModel):
    google_books_api_key: str | None = None
