from typing import Protocol
from pathlib import Path
from .data import BookMetadata
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
                authors=book.metadata.get_value("creator"),
                publisher=book.metadata.get_value("publisher"),
                languages=book.metadata.get_value("language"),
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