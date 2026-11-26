from math import log2, floor
from more_itertools import roundrobin
from pymupdf import Document
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


def get_pdf_isbn(): ... #TODO


def get_page_intervals(page_count: int):
    SCALE = 8

    excerpt_count = max(1, floor(log2(page_count / SCALE)))
    interval = page_count / excerpt_count

    return [
        {
            "begin": floor(i * interval),
            "end": (floor((i + 1) * interval)),
            "mid": (floor((i + 0.5) * interval)),
        }
        for i in range(excerpt_count)
    ]


def next_page_in_interval(begin: int, end: int, mid: int):
    left = range(mid, begin - 1, -1)
    right = range(mid + 1, end, 1)
    yield from roundrobin(left, right)


def get_pdf_excerpt(pdf: Document, begin: int, end: int, mid: int, min_word_count=300):
    candidate = []
    for page in next_page_in_interval(begin, end, mid):
        candidate.extend(pdf[page].get_text().split())
        if len(candidate) >= min_word_count:
            break
    return " ".join(candidate)
