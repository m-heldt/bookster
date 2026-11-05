from epublib import EPUB
from epublib.package.metadata import ValuedMetadataItem, BookMetadata
from pydantic_extra_types.isbn import ISBN

from .isbn import parse_isbn


def get_metadata_values(metadata: BookMetadata, name: str) -> ValuedMetadataItem:
    return [
        item.value
        for item in metadata.items
        if isinstance(item, ValuedMetadataItem) and item.name == name
    ]


def get_isbn(metadata: BookMetadata) -> ISBN | None:
    isbn_candidates = get_metadata_values(metadata, "identifier")

    for candidate in isbn_candidates:
        candidate = parse_isbn(candidate)
        if candidate != None:
            return ISBN(candidate)
