from abc import ABC, abstractmethod
from typing import override, final
from pathlib import Path
from .data import Book, BookMetadata, Person
from epublib import EPUB
from .utils import get_metadata_values, get_isbn

class BookAdapter(ABC):
    @final
    def load_book(self, path: Path) -> Book:
        metadata = self.read_metadata(path)
        return Book(path=path, metadata=metadata)

    
    @abstractmethod
    def read_metadata(self, path: Path) -> BookMetadata:
        ...

    @abstractmethod
    def write_metadata(self, path: Path, metadata: BookMetadata) -> None:
        ...


class EPUBAdapter(BookAdapter):
    @override
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

    @override
    def write_metadata(self, path: Path, metadata: BookMetadata) -> None:
        ...


class PDFAdapter(BookAdapter):
    @override
    def read_metadata(self, path: Path) -> BookMetadata:
        return BookMetadata()

    @override
    def write_metadata(self, path: Path, metadata: BookMetadata) -> None:
        ...