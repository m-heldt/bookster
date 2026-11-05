import bs4
import pytest
from epublib.package.metadata import BookMetadata, GenericMetadataItem
from pydantic_extra_types.isbn import ISBN

from bookster.utils import get_isbn, get_metadata_values

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


def test_get_isbn_returns_isbn_instance(metadata):
    metadata.add_dc("identifier", f"urn:isbn:{ISBN13}")

    assert isinstance(get_isbn(metadata), ISBN)
