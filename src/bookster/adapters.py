from typing import Protocol
from pathlib import Path
from .data import BookMetadata, Person
from epublib import EPUB
from .utils import get_metadata_values, get_isbn

class MetadataAdapter(Protocol):
    def read_metadata(self, path: Path) -> BookMetadata:
        ...

    def write_metadata(self, path: Path, metadata: BookMetadata) -> None:
        ...


class EPUBAdapter():
    def read_metadata(self, path: Path) -> BookMetadata:
        '''Reads EPUB metadata
        '''
        with EPUB(path) as book:
            metadata = BookMetadata(
                title=book.metadata.get_value("title"),
                contributors=[
                    Person(name=name)
                    for name in get_metadata_values(book.metadata, "creator")
                    if name.strip()
                ],
                publisher=book.metadata.get_value("publisher"),
                languages=get_metadata_values(book.metadata, "language"),
                isbn=get_isbn(book.metadata),
                description=book.metadata.get_value("description"),
                subjects=get_metadata_values(book.metadata, "subject")
            )
        return metadata

    def write_metadata(self, path: Path, metadata: BookMetadata) -> None:
        ...


class PDFAdapter():
    def read_metadata(self, path: Path) -> BookMetadata:
        return BookMetadata()

    def write_metadata(self, path: Path, metadata: BookMetadata) -> None:
        ...