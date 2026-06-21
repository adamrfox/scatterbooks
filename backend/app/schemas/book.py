from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.category import CategoryOut
from app.schemas.edition import EditionOut


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    author: str = Field(min_length=1, max_length=255)
    category_id: int | None = None
    edition_id: int | None = None
    notes: str | None = None
    year: int | None = None


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    author: str | None = Field(default=None, min_length=1, max_length=255)
    category_id: int | None = None
    edition_id: int | None = None
    notes: str | None = None
    year: int | None = None


class BookOut(BaseModel):
    id: int
    title: str
    author: str
    category_id: int | None
    edition_id: int | None
    category: CategoryOut | None
    edition: EditionOut | None
    cover_image_id: int | None
    notes: str | None
    year: int | None
    created_by: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
