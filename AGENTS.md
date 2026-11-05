# AGENTS.md

Guidance for coding agents working in this repository.

## Overview

Bookster is a command-line tool for reading and fixing ebook metadata in EPUB
and PDF files. The goal is to clean up a personal ebook library: fix EPUB
metadata, embed proper metadata in PDFs, and later use an LLM to normalize
every book's metadata against one spec.

The project is early. What works today:

- Reading EPUB metadata into a `BookMetadata` model (`EPUBAdapter.read_metadata`).
- Extracting and validating ISBNs from EPUB identifiers (normalized to ISBN-13).
- An `inspect` CLI command that prints a book's metadata.

Stubs, not yet implemented: `EPUBAdapter.write_metadata`, all of `PDFAdapter`
(`read_metadata` returns an empty `BookMetadata`), the `metadata` CLI command
(only prints the filename), and the `Book` class in `data.py` (unused).

Several dependencies in `pyproject.toml` are declared for planned work and are
not imported anywhere yet: `openai`, `arize-phoenix-otel`,
`openinference-instrumentation-openai`, `pikepdf`, `pymupdf`, `pypdf`,
`rapidfuzz`, `langcodes`, `httpx2`, `rich`. Check what is already declared
before adding a new dependency.

## Layout

```
src/bookster/          # package (src layout, built with uv_build)
  __init__.py          # empty
  main.py              # Typer app: `inspect`, `metadata` commands; the `bookster` script
  adapters.py          # MetadataAdapter Protocol + EPUBAdapter, PDFAdapter
  data.py              # pydantic BookMetadata model, Book class
  utils.py             # EPUB metadata helpers: get_metadata_values, get_isbn, _extract_isbn
tests/
  test_utils.py        # pytest tests for utils.py
.agents/skills/, .claude/skills/   # agent skills (see "Agent skills" below)
ebooks/                # sample books, gitignored, main checkout only
notebooks/             # scratch notebooks, gitignored
```

## Commands

Python 3.13 and [uv](https://docs.astral.sh/uv/). Run everything through `uv run`.

```bash
uv sync                                         # install deps, including the dev group
uv run pytest                                   # run the test suite
uv run pytest --cov=bookster                    # with coverage (pytest-cov)
uv run pytest tests/test_utils.py -k isbn       # a subset
uv run bookster --help                          # the CLI
uv run bookster inspect path/to/book.epub
```

The `bookster` console script points at the Typer `app` in `bookster/main.py`
(`[project.scripts]` in `pyproject.toml`). New commands go on that `app`.

No linter, formatter or type checker is configured. Don't add one, or reformat
existing files wholesale, unless asked.

## Architecture

- **`BookMetadata`** (`data.py`) is the format-independent model every adapter
  reads into and writes from. It is a pydantic `BaseModel` with all fields
  optional: `title`, `authors`, `publisher`, `languages`, `isbn`
  (`pydantic_extra_types.isbn.ISBN`), `description`, `subjects`
  (a list, default empty). `authors` and `languages` are single strings for now.
- **`MetadataAdapter`** (`adapters.py`) is a `typing.Protocol` with
  `read_metadata(path) -> BookMetadata` and `write_metadata(path, metadata) -> None`.
  Each file format gets one adapter class that satisfies it structurally (no
  inheritance). Add new formats as new adapters, and keep format-specific code
  inside them.
- **`EPUBAdapter`** uses `epublib.EPUB` as a context manager and reads Dublin
  Core values via `book.metadata.get_value(...)`; repeated fields like `subject`
  go through `utils.get_metadata_values`.
- **`utils.py`** works on epublib's metadata objects. `get_isbn` scans every
  `identifier` item and returns the first one that `_extract_isbn` can validate.
  `_extract_isbn` strips `urn:isbn:`, `isbn:`, `isbn-13:`, `isbn13:` style
  prefixes (case-insensitive), spaces and hyphens, uppercases a trailing `x`,
  and validates with pydantic's `ISBN` type, which converts ISBN-10 to ISBN-13.
  It returns `None` for anything invalid instead of raising.
- **CLI** (`main.py`) is a plain `typer.Typer()` app. `inspect` currently always
  uses `EPUBAdapter` regardless of file extension.

### Watch out: two classes named `BookMetadata`

- `bookster.data.BookMetadata` is this project's pydantic model.
- `epublib.package.metadata.BookMetadata` is epublib's OPF `<metadata>` block,
  and it is what `utils.py` and the tests import.

Check which one a module imports before using it, and alias one of them when a
module needs both.

## Conventions

- Type hints everywhere, using `X | None` and builtin generics (`list[str]`).
- Docstrings in Google style (`Args:` / `Returns:`), as in `_extract_isbn`.
- Prefix module-private helpers with `_`.
- Parsing helpers return `None` on bad input rather than raising, so one
  malformed identifier doesn't stop a book from loading.
- For CLI work, load the `typer` agent skill and follow it.

## Testing

- Tests live in `tests/`, one `test_<module>.py` per module, using plain pytest
  functions, fixtures and `@pytest.mark.parametrize`. Group tests with
  `# --- function_name ---` comment headers.
- Build EPUB metadata in memory instead of using real files:
  `BookMetadata(soup=bs4.BeautifulSoup("", "xml"))` from epublib, then
  `add_dc(...)`, `add(..., cls=GenericMetadataItem)` or `add_link(...)`
  (see the `metadata` fixture in `tests/test_utils.py`).
- Use ISBNs with valid check digits (the tests use `9780306406157` /
  `0306406152`), and cover the invalid cases explicitly.
- Add or update tests with every behavior change, and run `uv run pytest`
  before committing.

## Sample books and secrets

- `ebooks/` holds the owner's real library for manual testing. It exists only
  in the main checkout (`/Volumes/Workspace/01_Projects/bookster`), not in
  worktrees. Never commit these files, and never write to them in place: copy a
  book to a temp directory before testing anything that writes metadata.
- `.envrc` holds secrets (API keys). It is gitignored. Never commit it, print
  its contents, or copy values from it into code, tests or logs.

## Git workflow

- Commit straight to `main`; history is linear, with no feature branches or PRs.
- Use Conventional Commits scoped by module, for example `feat(adapters): ...`,
  `fix(utils): ...`, `test(utils): ...`, `build(deps): ...`,
  `chore(gitignore): ...`, `docs: ...`.
- Keep commits small and focused. Commit locally; don't push unless asked.

## Agent skills

Skills are managed by [Library Skills](https://library-skills.io) and mirrored in
`.agents/skills/` and `.claude/skills/`. The `typer` skill is a symlink into
`.venv/lib/python3.13/site-packages/typer/.agents/skills/typer`, so it only
resolves after `uv sync`. If a skill link is broken or stale, see the
`library-skills` skill (`uvx library-skills`).
