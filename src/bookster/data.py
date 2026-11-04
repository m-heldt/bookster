from epublib import EPUB
from epublib.package.metadata import DublinCoreMetadataItem
from pydantic import BaseModel, Field
from pydantic_extra_types.isbn import ISBN
from pydantic.dataclasses import dataclass
from pathlib import Path


class BookMetadata(BaseModel):
    title: str | None = None
    authors: str | None = None
    publisher: str | None = None
    languages: str | None = None
    isbn: ISBN | str | None = None
    description: str | None = None
    subjects: list[str] = Field(default_factory=list)


class Book:
    path: Path
    metadata: BookMetadata
    category: tuple | None = None