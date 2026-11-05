import bs4
import pytest
from epublib.package.metadata import BookMetadata, GenericMetadataItem

from bookster.utils import _extract_isbn, get_isbn, get_metadata_values

# ISBN-13 / ISBN-10 pair for the same book, both with valid check digits.
ISBN13 = "9780306406157"
ISBN10 = "0306406152"


@pytest.fixture
def metadata() -> BookMetadata:
    """An empty, standalone EPUB metadata block."""
    return BookMetadata(soup=bs4.BeautifulSoup("", "xml"))


# --- get_metadata_values ----------------------------------------------------


def test_get_metadata_values_returns_values_in_order(metadata):
    metadata.add_dc("identifier", "urn:uuid:abc")
    metadata.add_dc("title", "A Book")
    metadata.add_dc("identifier", f"urn:isbn:{ISBN13}")

    assert get_metadata_values(metadata, "identifier") == [
        "urn:uuid:abc",
        f"urn:isbn:{ISBN13}",
    ]


def test_get_metadata_values_includes_non_dublin_core_items(metadata):
    metadata.add("identifier", ISBN13, cls=GenericMetadataItem)

    assert get_metadata_values(metadata, "identifier") == [ISBN13]


def test_get_metadata_values_ignores_link_items(metadata):
    metadata.add_link(
        href="https://example.com/record", rel="record", media_type="text/html"
    )
    metadata.add_dc("title", "A Book")

    assert get_metadata_values(metadata, "title") == ["A Book"]


def test_get_metadata_values_missing_name_returns_empty_list(metadata):
    metadata.add_dc("title", "A Book")

    assert get_metadata_values(metadata, "identifier") == []


# --- _extract_isbn ----------------------------------------------------------


@pytest.mark.parametrize(
    "candidate",
    [
        ISBN13,
        f"urn:isbn:{ISBN13}",
        f"URN:ISBN:{ISBN13}",
        "urn:isbn:978-0-306-40615-7",
        f"urn:isbn: {ISBN13}",
        f"isbn:{ISBN13}",
        f"ISBN: {ISBN13}",
        f"ISBN-13:{ISBN13}",
        "ISBN-13 : 978 0 306 40615 7",
        "978 0 306 40615 7",
    ],
)
def test_extract_isbn_strips_prefixes_and_separators(candidate):
    assert _extract_isbn(candidate) == ISBN13


@pytest.mark.parametrize(
    "candidate",
    [
        ISBN10,
        f"urn:isbn:{ISBN10}",
        "ISBN-10: 0-306-40615-2",
    ],
)
def test_extract_isbn_converts_isbn10_to_isbn13(candidate):
    assert _extract_isbn(candidate) == ISBN13


def test_extract_isbn_accepts_isbn10_with_x_check_digit():
    assert _extract_isbn("0-8044-2957-X") == "9780804429573"


def test_extract_isbn_accepts_lowercase_x_check_digit():
    assert _extract_isbn("080442957x") == "9780804429573"


@pytest.mark.parametrize("prefix", ["isbn13:", "ISBN10:", "isbn13 :"])
def test_extract_isbn_strips_unhyphenated_prefix(prefix):
    isbn = ISBN10 if "10" in prefix else ISBN13
    assert _extract_isbn(f"{prefix}{isbn}") == ISBN13


@pytest.mark.parametrize(
    "candidate",
    [
        "",
        "urn:uuid:12345678-1234-1234-1234-123456789abc",
        "9780306406158",  # wrong check digit
        "0306406153",  # wrong ISBN-10 check digit
        "97803064061",  # too short
        "not an isbn",
    ],
)
def test_extract_isbn_returns_none_for_invalid(candidate):
    assert _extract_isbn(candidate) is None


# --- get_isbn ---------------------------------------------------------------


def test_get_isbn_no_identifiers_returns_none(metadata):
    metadata.add_dc("title", "A Book")

    assert get_isbn(metadata) is None


def test_get_isbn_no_valid_isbn_returns_none(metadata):
    metadata.add_dc("identifier", "urn:uuid:abc")
    metadata.add_dc("identifier", "urn:isbn:9780306406158")

    assert get_isbn(metadata) is None


def test_get_isbn_skips_non_isbn_identifiers(metadata):
    metadata.add_dc("identifier", "urn:uuid:abc")
    metadata.add_dc("identifier", f"urn:isbn:{ISBN10}")

    assert get_isbn(metadata) == ISBN13


def test_get_isbn_returns_first_valid_isbn(metadata):
    metadata.add_dc("identifier", "urn:isbn:9780804429573")
    metadata.add_dc("identifier", f"urn:isbn:{ISBN13}")

    assert get_isbn(metadata) == "9780804429573"


def test_get_isbn_ignores_isbn_under_other_names(metadata):
    metadata.add_dc("source", f"urn:isbn:{ISBN13}")

    assert get_isbn(metadata) is None
