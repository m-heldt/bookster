from epublib.package.metadata import ValuedMetadataItem, BookMetadata
from pydantic_extra_types.isbn import ISBN

from .isbn import parse_isbn


def get_metadata_values(metadata: BookMetadata, name: str) -> list[str]:
    return [
        item.value
        for item in metadata.items
        if isinstance(item, ValuedMetadataItem) and item.name == name
    ]


def get_isbn(metadata: BookMetadata) -> ISBN | None:
    """Return the first valid ISBN among the EPUB's identifiers.

    Args:
        metadata: The EPUB's OPF metadata block.

    Returns:
        The first identifier that parses as an ISBN, normalized to ISBN-13,
        or None if there is none.
    """
    for identifier in get_metadata_values(metadata, "identifier"):
        if (isbn := parse_isbn(identifier)) is not None:
            return isbn
    return None
