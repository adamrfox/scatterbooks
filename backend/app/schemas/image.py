from datetime import datetime

from pydantic import BaseModel, Field


class BookImageOut(BaseModel):
    id: int
    book_id: int
    position: int
    content_type: str
    width: int | None
    height: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BookImageReorder(BaseModel):
    position: int = Field(ge=0, le=4)
