import re

from pydantic import TypeAdapter, ValidationError
from pydantic_extra_types.isbn import ISBN

_ISBN_ADAPTER = TypeAdapter(ISBN)

_PREFIX = re.compile(r"^(urn:isbn:|isbn(-?1[03])?\s*:)\s*", flags=re.IGNORECASE)
_SEPARATORS = re.compile(r"[\s-]")


def parse_isbn(text: str) -> ISBN | None:
    """Extract and validate an ISBN from free text.

    Works on any string, whatever its source: an EPUB identifier, PDF
    metadata, or a value scraped from a metadata provider.

    Args:
        text: A candidate such as "urn:isbn:978-0-306-40615-7" or
            "ISBN-10: 0-306-40615-2".

    Returns:
        The ISBN normalized to ISBN-13 without separators,
        or None if the text is not a valid ISBN.
    """
    candidate = _PREFIX.sub("", text)
    candidate = _SEPARATORS.sub("", candidate).upper()

    try:
        return ISBN(_ISBN_ADAPTER.validate_python(candidate))
    except ValidationError:
        return None
