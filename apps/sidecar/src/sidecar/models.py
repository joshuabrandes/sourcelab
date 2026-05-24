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


class ChunkElement(DocumentElement):
    model_config = ConfigDict(extra="forbid")

    id: str


class DocumentMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    author: str | None = None
    pageCount: int | None = Field(default=None, ge=1)
    imageWidth: int | None = Field(default=None, ge=1)
    imageHeight: int | None = Field(default=None, ge=1)
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
    contentType: ContentType
    filePath: str | None = None
    sourceUrl: str | None = None


class DocumentChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sourceId: str
    content: str
    tokenCount: int = Field(ge=0)
    startElement: str
    endElement: str
    headingContext: str | None = None
    page: int | None = Field(default=None, ge=1)
    position: int = Field(ge=0)


class ChunkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sourceId: str
    elements: list[ChunkElement]
    chunkSize: int = Field(default=512, ge=1)
    chunkOverlap: int = Field(default=64, ge=0)


class ChunkResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sourceId: str
    chunks: list[DocumentChunk]

    @field_validator("chunks")
    @classmethod
    def validate_positions(cls, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        expected_position = 0
        for chunk in chunks:
            if chunk.position != expected_position:
                raise ValueError("chunks must have contiguous positions starting at 0")
            expected_position += 1

        return chunks
