from datetime import datetime

from pydantic import BaseModel, Field


class EditionOut(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class EditionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class EditionUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
