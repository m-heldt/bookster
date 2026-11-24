from abc import ABC, abstractmethod
from typing import override, final
from pathlib import Path
from .data import Book, BookMetadata, Person
from epublib import EPUB
import pikepdf
from .utils import get_metadata_values, get_isbn


class BookAdapter(ABC):
    @final
    def load_book(self, path: Path) -> Book:
        metadata = self.read_metadata(path)
        return Book(path=path, metadata=metadata)

    @abstractmethod
    def read_metadata(self, path: Path) -> BookMetadata: ...

    @abstractmethod
    def write_metadata(self, path: Path, metadata: BookMetadata) -> None: ...


class EPUBAdapter(BookAdapter):
    @override
    def read_metadata(self, path: Path) -> BookMetadata:
        """Reads EPUB metadata"""
        with EPUB(path) as book:
            return BookMetadata(
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
                subjects=get_metadata_values(book.metadata, "subject"),
            )

    @override
    def write_metadata(self, path: Path, metadata: BookMetadata) -> None: ...


class PDFAdapter(BookAdapter):
    @staticmethod
    def _text_values(value: str | list[str] | set[str] | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        if isinstance(value, set):
            value = sorted(value)
        return [text for item in value if (text := item.strip())]

    @override
    def read_metadata(self, path: Path) -> BookMetadata:
        with pikepdf.open(path) as pdf:
            metadata = pdf.open_metadata(set_pikepdf_as_editor=False)
            creators = self._text_values(metadata.get("dc:creator"))
            publishers = self._text_values(metadata.get("dc:publisher"))
            return BookMetadata(
                title=metadata.get("dc:title"),
                contributors=[Person(name=name) for name in creators],
                publisher=next(iter(publishers), None),
                languages=self._text_values(metadata.get("dc:language")),
                # TODO: Research where PDFs store ISBNs. The sample PDFs lack dc:identifier.
                isbn=None,
                description=metadata.get("dc:description"),
                subjects=self._text_values(metadata.get("dc:subject")),
            )

    @override
    def write_metadata(self, path: Path, metadata: BookMetadata) -> None: ...
