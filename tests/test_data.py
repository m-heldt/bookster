import unicodedata
from pathlib import Path

import pytest
from pydantic import ValidationError

from bookster.data import Book, BookMetadata, Category, Person, Role, Taxonomy

# ISBN-13 / ISBN-10 pair for the same book, both with valid check digits.
ISBN13 = "9780306406157"
ISBN10 = "0306406152"


# --- Role -------------------------------------------------------------------


def test_role_from_marc_code():
    assert Role("trl") is Role.TRANSLATOR


def test_role_is_case_insensitive():
    assert Role("AUT") is Role.AUTHOR


@pytest.mark.parametrize("code", ["bkp", "xyz", ""])
def test_role_unknown_code_maps_to_other(code):
    assert Role(code) is Role.OTHER


# --- Person -----------------------------------------------------------------


def test_person_defaults_to_author():
    assert Person(name="Ken Mogi").role is Role.AUTHOR


def test_person_strips_name():
    assert Person(name="  Ken Mogi ").name == "Ken Mogi"


@pytest.mark.parametrize("name", ["", "   "])
def test_person_rejects_blank_name(name):
    with pytest.raises(ValidationError):
        Person(name=name)


def test_person_blank_name_parts_become_none():
    person = Person(name="Ken Mogi", family_name=" ", given_names="")

    assert person.family_name is None
    assert person.given_names is None


def test_person_sort_name_from_family_and_given():
    person = Person(
        name="Jordan B. Peterson", family_name="Peterson", given_names="Jordan B."
    )

    assert person.sort_name == "Peterson, Jordan B."


def test_person_sort_name_family_only():
    assert Person(name="Swami Rama", family_name="Rama").sort_name == "Rama"


def test_person_sort_name_falls_back_to_name():
    assert Person(name="Ken Mogi").sort_name == "Ken Mogi"


def test_person_is_immutable():
    person = Person(name="Ken Mogi")

    with pytest.raises(ValidationError):
        person.name = "Someone Else"


# --- BookMetadata -----------------------------------------------------------


def test_metadata_defaults_are_empty():
    metadata = BookMetadata()

    assert metadata.title is None
    assert metadata.contributors == []
    assert metadata.languages == []
    assert metadata.subjects == []


def test_metadata_blank_strings_become_none():
    metadata = BookMetadata(title="  ", publisher="", description=" \n")

    assert metadata.title is None
    assert metadata.publisher is None
    assert metadata.description is None


def test_metadata_strips_strings():
    assert BookMetadata(title="  Jestem dość ").title == "Jestem dość"


def test_metadata_lists_drop_blanks_and_duplicates_keeping_order():
    metadata = BookMetadata(languages=["pl", " ", "en", "pl"], subjects=["b", "a", "b"])

    assert metadata.languages == ["pl", "en"]
    assert metadata.subjects == ["b", "a"]


def test_metadata_isbn_is_normalized_to_isbn13():
    assert BookMetadata(isbn=ISBN10).isbn == ISBN13


def test_metadata_rejects_invalid_isbn():
    with pytest.raises(ValidationError):
        BookMetadata(isbn="9780306406158")


def test_metadata_blank_isbn_becomes_none():
    assert BookMetadata(isbn=" ").isbn is None


def test_metadata_validates_on_assignment():
    metadata = BookMetadata()

    with pytest.raises(ValidationError):
        metadata.isbn = "not an isbn"


def test_metadata_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        BookMetadata(authors="Ken Mogi")


def test_metadata_rejects_negative_series_index():
    with pytest.raises(ValidationError):
        BookMetadata(series_index=-1)


def test_metadata_accepts_fractional_series_index():
    assert BookMetadata(series_index=2.5).series_index == 2.5


def test_metadata_authors_and_translators_are_views_in_order():
    first = Person(name="Anne-Hélène Clair")
    translator = Person(name="Jan Kowalski", role=Role.TRANSLATOR)
    second = Person(name="Vincent Trybou")
    metadata = BookMetadata(contributors=[first, translator, second])

    assert metadata.authors == [first, second]
    assert metadata.translators == [translator]


def test_metadata_drops_duplicate_contributors():
    person = Person(name="Ken Mogi")

    assert BookMetadata(contributors=[person, person]).contributors == [person]


def test_metadata_keeps_same_person_in_different_roles():
    author = Person(name="Ken Mogi")
    translator = Person(name="Ken Mogi", role=Role.TRANSLATOR)

    assert BookMetadata(contributors=[author, translator]).contributors == [
        author,
        translator,
    ]


# --- Category ---------------------------------------------------------------


def test_category_parse_and_str_round_trip():
    category = Category.parse("Psychology/Disorders & Treatment/Trauma")

    assert category.parts == ("Psychology", "Disorders & Treatment", "Trauma")
    assert str(category) == "Psychology/Disorders & Treatment/Trauma"


def test_category_normalizes_to_nfc():
    decomposed = unicodedata.normalize("NFD", "Zdrowie i żywienie")

    assert Category.parse(decomposed) == Category.parse("Zdrowie i żywienie")


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Psychology/",
        "/Psychology",
        "Psychology//Trauma",
        "Psychology/..",
        "IT/Development ",  # trailing space: the cause of the DOGVES~C folder
        " IT",
        "Science/Etc.",
        "IT/C:Drive",
        "Psychology/What?",
        "IT/A|B",
        "IT/Tab\tName",
    ],
)
def test_category_rejects_unsafe_names(text):
    with pytest.raises(ValidationError):
        Category.parse(text)


def test_category_rejects_backslash():
    with pytest.raises(ValidationError):
        Category(parts=("IT", "A\\B"))


def test_category_from_path():
    root = Path("/Volumes/Lexar/Books")
    book = root / "Psychology" / "Trauma" / "book.epub"

    assert Category.from_path(book, root) == Category.parse("Psychology/Trauma")


def test_category_from_path_in_root_is_none():
    root = Path("/Volumes/Lexar/Books")

    assert Category.from_path(root / "book.epub", root) is None


def test_category_as_path():
    assert Category.parse("Politics/History").as_path() == Path("Politics/History")


def test_category_name_and_parent():
    category = Category.parse("Politics/History/PRL")

    assert category.name == "PRL"
    assert category.parent == Category.parse("Politics/History")
    assert Category.parse("Politics").parent is None


def test_category_is_ancestor_of():
    politics = Category.parse("Politics")
    prl = Category.parse("Politics/History/PRL")

    assert politics.is_ancestor_of(prl)
    assert not prl.is_ancestor_of(politics)
    assert not politics.is_ancestor_of(politics)
    assert not Category.parse("Pol").is_ancestor_of(politics)


def test_category_is_hashable():
    assert len({Category.parse("A/B"), Category.parse("A/B")}) == 1


# --- Taxonomy ---------------------------------------------------------------


@pytest.fixture
def taxonomy() -> Taxonomy:
    return Taxonomy.from_dict(
        {
            "exclude": ["Create/Photography"],
            "categories": {
                "Economics/Monetary Systems & MMT": "Money and central banks",
                "Economics/Other": "",
                "Psychology/Disorders & Treatment/Trauma": "",
                "Psychology/Productivity": "",
                "Travel": "",
                "Create/Photography/Portret": "",
                "Create/Writing": "",
            },
        }
    )


def test_taxonomy_options_add_other_under_every_parent(taxonomy):
    assert [str(category) for category in taxonomy.options] == [
        "Create/Other",
        "Create/Writing",
        "Economics/Monetary Systems & MMT",
        "Economics/Other",
        "Other",
        "Psychology/Disorders & Treatment/Other",
        "Psychology/Disorders & Treatment/Trauma",
        "Psychology/Other",
        "Psychology/Productivity",
        "Travel",
    ]


def test_taxonomy_contains_only_options(taxonomy):
    assert Category.parse("Psychology/Other") in taxonomy
    assert Category.parse("Travel") in taxonomy
    assert Category.parse("Psychology") not in taxonomy  # parent folder
    assert Category.parse("Fiction") not in taxonomy  # not listed


def test_taxonomy_excluded_subtree_is_not_an_option(taxonomy):
    portret = Category.parse("Create/Photography/Portret")

    assert taxonomy.is_excluded(portret)
    assert taxonomy.is_excluded(Category.parse("Create/Photography"))
    assert portret not in taxonomy
    assert Category.parse("Create/Photography/Other") not in taxonomy


def test_taxonomy_description(taxonomy):
    mmt = Category.parse("Economics/Monetary Systems & MMT")

    assert taxonomy.description(mmt) == "Money and central banks"
    assert taxonomy.description(Category.parse("Travel")) is None


def test_taxonomy_custom_other_name():
    taxonomy = Taxonomy.from_dict({"other": "Inne", "categories": {"A/B": ""}})

    assert [str(category) for category in taxonomy.options] == ["A/B", "A/Inne", "Inne"]


def test_taxonomy_empty_offers_only_top_level_other():
    assert [str(c) for c in Taxonomy.from_dict({}).options] == ["Other"]


def test_taxonomy_rejects_leaf_that_has_subcategories():
    with pytest.raises(ValidationError, match="has a subcategory"):
        Taxonomy.from_dict({"categories": {"Psychology": "", "Psychology/Trauma": ""}})


def test_taxonomy_rejects_other_as_parent_folder():
    with pytest.raises(ValidationError, match="can only be a leaf"):
        Taxonomy.from_dict({"categories": {"Economics/Other/Old": ""}})


def test_taxonomy_rejects_unsafe_category_name():
    with pytest.raises(ValidationError):
        Taxonomy.from_dict({"categories": {"IT/Development ": ""}})


def test_taxonomy_rejects_description_for_unlisted_category():
    with pytest.raises(ValidationError, match="unlisted"):
        Taxonomy(
            leaves=frozenset({Category.parse("A")}),
            descriptions={"B": "not a leaf"},
        )


def test_taxonomy_from_toml(tmp_path):
    config = tmp_path / "bookster.toml"
    config.write_text(
        """
library_root = "/Volumes/Lexar/Books"
other = "Other"
exclude = ["Create/Photography"]

[categories]
"Politics/History/World War II" = ""
"Science/Physics" = "Physics, popular and textbooks"
""",
        encoding="utf-8",
    )

    taxonomy = Taxonomy.from_toml(config)

    assert Category.parse("Politics/History/World War II") in taxonomy
    assert Category.parse("Politics/History/Other") in taxonomy
    assert taxonomy.description(Category.parse("Science/Physics")) == (
        "Physics, popular and textbooks"
    )
    assert taxonomy.is_excluded(Category.parse("Create/Photography/Portret"))


# --- Book -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("filename", "expected"),
    [("book.epub", "epub"), ("BOOK.PDF", "pdf"), ("archive.tar.gz", "gz"), ("noext", "")],
)
def test_book_format(filename, expected):
    assert Book(path=Path(filename)).format == expected


def test_book_defaults():
    book = Book(path=Path("book.epub"))

    assert book.metadata == BookMetadata()
    assert book.category is None


def test_book_category_from_string_is_validated():
    with pytest.raises(ValidationError):
        Book(path=Path("book.epub"), category={"parts": ["IT/Development "]})
