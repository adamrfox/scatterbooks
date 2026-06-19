from pydantic import BaseModel


class IsbnLookupResult(BaseModel):
    isbn: str
    title: str | None
    author: str | None
