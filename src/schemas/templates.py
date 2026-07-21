from pydantic import BaseModel, Field
from typing import Any

class TemplateCreate(BaseModel):
    code: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[a-z0-9_]+$",
    )

    subject: str = Field(
        min_length=3,
        max_length=150,
    )

    body: str = Field(
        min_length=5,
        max_length=5000,
    )


class TemplateResponse(BaseModel):
    code: str
    subject:str
    body: str


class TemplateRenderRequest(BaseModel):
    context: dict[str, Any]


class TemplateRenderResponse(BaseModel):
    subject:str
    body: str