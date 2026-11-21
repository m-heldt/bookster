import re
import tomllib
import unicodedata
from enum import StrEnum
from functools import cached_property
from pathlib import Path
from typing import Any, Self, Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic_extra_types.isbn import ISBN


class Role(StrEnum):
    """Contributor roles as MARC relator codes, the vocabulary EPUB uses for opf:role."""

    AUTHOR = "aut"
    TRANSLATOR = "trl"
    EDITOR = "edt"
    ILLUSTRATOR = "ill"
    INTRODUCTION = "aui"
    NARRATOR = "nrt"
    OTHER = "oth"

    @classmethod
    def _missing_(cls, value: object) -> "Role":
        """Map codes case-insensitively, and anything unknown to OTHER."""
        if isinstance(value, str):
            for member in cls:
                if member.value == value.strip().lower():
                    return member
        return cls.OTHER


class Person(BaseModel):
    """A person credited on a book, such as an author or translator."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1)
    family_name: str | None = None
    given_names: str | None = None
    role: Role = Role.AUTHOR

    @field_validator("family_name", "given_names", mode="before")
    @classmethod
    def _blank_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @computed_field
    @property
    def sort_name(self) -> str:
        """Name for sorting, e.g. "Peterson, Jordan B." (EPUB file-as)."""
        if self.family_name and self.given_names:
            return f"{self.family_name}, {self.given_names}"
        return self.family_name or self.name


_OPTIONAL_STR_FIELDS = (
    "title",
    "publisher",
    "isbn",
    "series",
    "original_title",
    "original_language",
    "description",
)


class BookMetadata(BaseModel):
    """Format-independent book metadata that every adapter reads into and writes from."""

    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, validate_assignment=True
    )

    title: str | None = None
    contributors: list[Person] = Field(default_factory=list)
    publisher: str | None = None
    year: int | None = None
    languages: list[str] = Field(default_factory=list)
    isbn: ISBN | None = None
    series: str | None = None
    series_index: float | None = Field(default=None, ge=0)
    original_title: str | None = None
    original_language: str | None = None
    subjects: list[str] = Field(default_factory=list)
    description: str | None = None

    @field_validator(*_OPTIONAL_STR_FIELDS, mode="before")
    @classmethod
    def _blank_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("languages", "subjects")
    @classmethod
    def _clean_strings(cls, values: list[str]) -> list[str]:
        """Drop blank items and duplicates, keeping the original order."""
        return list(dict.fromkeys(value for value in values if value))

    @field_validator("contributors")
    @classmethod
    def _dedupe_contributors(cls, people: list[Person]) -> list[Person]:
        return list(dict.fromkeys(people))

    @property
    def authors(self) -> list[Person]:
        return [person for person in self.contributors if person.role is Role.AUTHOR]

    @property
    def translators(self) -> list[Person]:
        return [
            person for person in self.contributors if person.role is Role.TRANSLATOR
        ]


# Characters that are invalid in folder names on exFAT/Windows, plus control characters.
_FORBIDDEN_IN_PART = re.compile(r'[/\\:*?"<>|\x00-\x1f\x7f]')


class Category(BaseModel):
    """A folder in the library's category tree, e.g. Psychology/Trauma."""

    model_config = ConfigDict(frozen=True)

    parts: tuple[str, ...] = Field(min_length=1)

    @field_validator("parts")
    @classmethod
    def _validate_parts(cls, parts: tuple[str, ...]) -> tuple[str, ...]:
        """NFC-normalize each part and reject names unsafe as folder names.

        Bad names are rejected rather than cleaned up, because a cleaned-up
        name would no longer match the folder it came from.
        """
        normalized = []
        for part in parts:
            part = unicodedata.normalize("NFC", part)
            if part in {"", ".", ".."}:
                raise ValueError(f"invalid category part: {part!r}")
            if part != part.strip():
                raise ValueError(
                    f"category part has leading or trailing whitespace: {part!r}"
                )
            if part.endswith("."):
                raise ValueError(f"category part ends with a dot: {part!r}")
            if _FORBIDDEN_IN_PART.search(part):
                raise ValueError(f"category part has a forbidden character: {part!r}")
            normalized.append(part)
        return tuple(normalized)

    @classmethod
    def parse(cls, text: str) -> Self:
        """Build a category from a slash-separated path, e.g. "Psychology/Trauma"."""
        return cls(parts=tuple(text.split("/")))

    @classmethod
    def from_path(cls, book_path: Path, root: Path) -> Self | None:
        """Return the category of a book from its folder under the library root.

        Args:
            book_path: Path to the book file.
            root: The library root.

        Returns:
            The category, or None for a book directly in the root.
        """
        parts = book_path.parent.relative_to(root).parts
        return cls(parts=parts) if parts else None

    @property
    def name(self) -> str:
        return self.parts[-1]

    @property
    def parent(self) -> "Category | None":
        return Category(parts=self.parts[:-1]) if len(self.parts) > 1 else None

    def is_ancestor_of(self, other: "Category") -> bool:
        return (
            len(self.parts) < len(other.parts)
            and other.parts[: len(self.parts)] == self.parts
        )

    def as_path(self) -> Path:
        return Path(*self.parts)

    def __str__(self) -> str:
        return "/".join(self.parts)


class Taxonomy(BaseModel):
    """The set of categories books can be filed under.

    Books live only in leaf folders. Every parent folder implicitly has an
    `Other` leaf, and so does the root, for books that fit no listed leaf.
    """

    model_config = ConfigDict(frozen=True)

    leaves: frozenset[Category]
    descriptions: dict[str, str] = Field(default_factory=dict)
    other: str = "Other"
    exclude: frozenset[Category] = frozenset()

    @model_validator(mode="after")
    def _check_tree(self) -> Self:
        Category(parts=(self.other,))  # the Other name must be a valid folder name

        for leaf in self.leaves:
            if self.other in leaf.parts[:-1]:
                raise ValueError(f"{self.other!r} can only be a leaf: {leaf}")
            for other in self.leaves:
                if leaf.is_ancestor_of(other):
                    raise ValueError(
                        f"{leaf} is listed as a leaf but has a subcategory {other}"
                    )

        leaf_names = {str(leaf) for leaf in self.leaves}
        unknown = set(self.descriptions) - leaf_names
        if unknown:
            raise ValueError(f"descriptions for unlisted categories: {sorted(unknown)}")
        return self

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a taxonomy from parsed config data.

        Args:
            data: A mapping with `categories` (leaf path to description, which
                may be empty), and optionally `other` and `exclude`.
        """
        categories: dict[str, str | None] = data.get("categories", {})
        leaves = {path: Category.parse(path) for path in categories}
        return cls(
            leaves=frozenset(leaves.values()),
            descriptions={
                str(leaves[path]): description
                for path, description in categories.items()
                if description
            },
            other=data.get("other", "Other"),
            exclude=frozenset(Category.parse(path) for path in data.get("exclude", [])),
        )

    @classmethod
    def from_toml(cls, path: Path) -> Self:
        with path.open("rb") as file:
            return cls.from_dict(tomllib.load(file))

    @cached_property
    def options(self) -> tuple[Category, ...]:
        """Every category a book can be filed under, sorted by path.

        The listed leaves, plus `<parent>/Other` for every parent folder and a
        top-level `Other`, minus anything inside an excluded subtree.
        """
        parents = {
            leaf.parts[:depth] for leaf in self.leaves for depth in range(len(leaf.parts))
        }
        others = {Category(parts=(*parent, self.other)) for parent in parents}
        if not parents:
            others.add(Category(parts=(self.other,)))
        candidates = self.leaves | others
        return tuple(
            sorted(
                (category for category in candidates if not self.is_excluded(category)),
                key=lambda category: category.parts,
            )
        )

    def is_excluded(self, category: Category) -> bool:
        return any(
            excluded == category or excluded.is_ancestor_of(category)
            for excluded in self.exclude
        )

    def description(self, category: Category) -> str | None:
        return self.descriptions.get(str(category))

    def __contains__(self, category: object) -> bool:
        return category in self._option_set

    @cached_property
    def _option_set(self) -> frozenset[Category]:
        return frozenset(self.options)


class Book(BaseModel):
    """An ebook file in the library, its metadata and its category."""

    model_config = ConfigDict(extra="forbid")

    path: Path
    metadata: BookMetadata = Field(default_factory=BookMetadata)
    category: Category | None = None

    @property
    def format(self) -> str:
        """The file format from the extension, e.g. "epub" or "pdf"."""
        return self.path.suffix.lower().removeprefix(".")
