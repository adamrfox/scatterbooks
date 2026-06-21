from datetime import datetime

from pydantic import BaseModel, Field


class WishListEntryImageOut(BaseModel):
    id: int
    wish_list_entry_id: int
    position: int
    content_type: str
    width: int | None
    height: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WishListEntryImageReorder(BaseModel):
    position: int = Field(ge=0, le=4)
