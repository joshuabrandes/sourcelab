from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ElementType(str, Enum):
    heading = "heading"
    paragraph = "paragraph"
    table = "table"
    image = "image"
    code = "code"
    list = "list"


class ContentType(str, Enum):
    pdf = "pdf"
    docx = "docx"
    pptx = "pptx"
    md = "md"
    txt = "txt"
    html = "html"
    url = "url"
    youtube = "youtube"
    image = "image"


class DocumentElement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: ElementType
    content: str
    position: int = Field(ge=0)
    page: int | None = Field(default=None, ge=1)
    level: int | None = Field(default=None, ge=1)
    metadata: dict[str, Any] | None = None


class DocumentMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    author: str | None = None
    pageCount: int | None = Field(default=None, ge=1)
    language: str | None = None
    createdAt: str | None = None
    extractedAt: str | None = None


class ExtractedDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sourceId: str
    title: str
    language: str | None = None
    contentType: ContentType
    metadata: DocumentMetadata
    elements: list[DocumentElement]

    @field_validator("elements")
    @classmethod
    def validate_positions(cls, elements: list[DocumentElement]) -> list[DocumentElement]:
        expected_position = 0
        for element in elements:
            if element.position != expected_position:
                raise ValueError("elements must have contiguous positions starting at 0")
            expected_position += 1

        return elements


class ExtractFileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sourceId: str
    filePath: str
