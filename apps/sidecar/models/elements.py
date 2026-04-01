from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class ElementType(str, Enum):
    heading = "heading"
    paragraph = "paragraph"
    table = "table"
    image = "image"
    code = "code"
    list = "list"


class DocumentElement(BaseModel):
    type: ElementType
    content: str
    page: Optional[int] = None
    position: int
    level: Optional[int] = None  # heading level
    metadata: Optional[dict[str, Any]] = None


class DocumentMetadata(BaseModel):
    author: Optional[str] = None
    pageCount: Optional[int] = None
    createdAt: Optional[str] = None
    extractedAt: str


class ExtractedDocument(BaseModel):
    sourceId: str
    title: str
    language: str
    contentType: str
    metadata: DocumentMetadata
    elements: list[DocumentElement]
