from pydantic import BaseModel


class IdentifyCoverResult(BaseModel):
    title: str | None
    author: str | None
