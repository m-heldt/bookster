from epublib import EPUB
from epublib.package.metadata import ValuedMetadataItem, BookMetadata
from pydantic_extra_types.isbn import ISBN
from pydantic import TypeAdapter, ValidationError
import re


def get_metadata_values(metadata: BookMetadata, name: str) -> ValuedMetadataItem:
    return [
        item.value
        for item in metadata.items
        if isinstance(item, ValuedMetadataItem) and item.name == name
    ]


def _extract_isbn(isbn_candidate: str) -> ISBN:
    '''Extract and validate ISBN from a candidate.

    Args:
        isbn_candidate: An EPUB identifier

    Returns:
        The normalized ISBN-13 without separators,
        or None if validation fails.
    '''
    isbn_adapter = TypeAdapter(ISBN)

    candidate = re.sub(
        pattern=r"^(urn:isbn:|isbn(-10|-13)?\s*:)\s*",
        repl="",
        string=isbn_candidate,
        flags=re.IGNORECASE,
    )

    candidate = re.sub(pattern=r"[\s-]", repl="", string=candidate)

    try:
        return isbn_adapter.validate_python(candidate)
    except ValidationError:
        return None


def get_isbn(metadata: BookMetadata) -> ISBN:
    isbn_candidates = get_metadata_values(metadata, "identifier")

    for candidate in isbn_candidates:
        candidate = _extract_isbn(candidate)
        if candidate != None:
            return ISBN(candidate)