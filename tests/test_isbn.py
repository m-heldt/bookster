import pytest
from pydantic_extra_types.isbn import ISBN

from bookster.isbn import parse_isbn

# ISBN-13 / ISBN-10 pair for the same book, both with valid check digits.
ISBN13 = "9780306406157"
ISBN10 = "0306406152"


# --- parse_isbn ------------------------------------------------------------


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
def testparse_isbn_strips_prefixes_and_separators(candidate):
    assert parse_isbn(candidate) == ISBN13


@pytest.mark.parametrize(
    "candidate",
    [
        ISBN10,
        f"urn:isbn:{ISBN10}",
        "ISBN-10: 0-306-40615-2",
    ],
)
def testparse_isbn_converts_isbn10_to_isbn13(candidate):
    assert parse_isbn(candidate) == ISBN13


def testparse_isbn_accepts_isbn10_with_x_check_digit():
    assert parse_isbn("0-8044-2957-X") == "9780804429573"


def testparse_isbn_accepts_lowercase_x_check_digit():
    assert parse_isbn("080442957x") == "9780804429573"


@pytest.mark.parametrize("prefix", ["isbn13:", "ISBN10:", "isbn13 :"])
def testparse_isbn_strips_unhyphenated_prefix(prefix):
    isbn = ISBN10 if "10" in prefix else ISBN13
    assert parse_isbn(f"{prefix}{isbn}") == ISBN13


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
def testparse_isbn_returns_none_for_invalid(candidate):
    assert parse_isbn(candidate) is None


def test_parse_isbn_returns_isbn_instance():
    assert isinstance(parse_isbn(ISBN10), ISBN)
