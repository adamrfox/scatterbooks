from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.category import CategoryOut
from app.schemas.edition import EditionOut


class WishListCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    is_public: bool = False


class WishListUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_public: bool | None = None


class WishListOut(BaseModel):
    id: int
    name: str
    is_public: bool
    owner_id: int
    owner_username: str
    entry_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WishListEntryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    author: str = Field(min_length=1, max_length=255)
    category_id: int | None = None
    edition_id: int | None = None
    notes: str | None = None
    year: int | None = None


class WishListEntryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    author: str | None = Field(default=None, min_length=1, max_length=255)
    category_id: int | None = None
    edition_id: int | None = None
    notes: str | None = None
    year: int | None = None


class WishListEntryOut(BaseModel):
    id: int
    wish_list_id: int
    title: str
    author: str
    category_id: int | None
    edition_id: int | None
    category: CategoryOut | None
    edition: EditionOut | None
    cover_image_id: int | None
    notes: str | None
    year: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
