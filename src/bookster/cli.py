import typer
from pathlib import Path
from rich import print as rprint
from rich.pretty import pprint
from rich.table import Table
from rich.console import Console
from bookster.adapters import EPUBAdapter
from bookster.data import BookMetadata, Role
from typing import Literal, Annotated

app = typer.Typer()

TRANSLATION = {
    "en": {
        "title": "Title",
        "author": "Author(s)",
        "publisher": "Publisher",
        "year": "Publication year",
        "languages": "Languages",
        "isbn": "ISBN",
        "series": "Series",
        "series_index": "Series index",
        "original_title": "Original title",
        "original_language": "Original language",
        "subjects": "Subjects",
        "description": "Description",
        "none": "Unknown",
    },
    "pl": {
        "title": "Tytuł",
        "author": "Autor",
        "publisher": "Wydawca",
        "year": "Rok wydania",
        "languages": "Języki",
        "isbn": "ISBN",
        "series": "Seria",
        "series_index": "Indeks serii",
        "original_title": "Tytuł oryginalny",
        "original_language": "Język oryginalny",
        "subjects": "Kategorie",
        "description": "Opis",
        "none": "Nieznany",
    },
}


@app.command(help="Show book metadata")
def inspect(book_path: Path, ui_language: Literal["en", "pl"] = "en") -> None:
    book_path = Path(book_path)
    rprint(f"Showing the metadata of: {book_path.name}")
    epub_adapter = EPUBAdapter()
    metadata = epub_adapter.read_metadata(path=book_path)

    table = Table(show_header=False)

    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column()

    for field in BookMetadata.model_fields:
        value = getattr(metadata, field)

        if field == "contributors":
            authors = [
                contributor.name
                for contributor in value
                if contributor.role == Role.AUTHOR
            ]
            table.add_row(TRANSLATION[ui_language]["author"], ", ".join(authors))
        elif value is None or not value:
            table.add_row(
                TRANSLATION[ui_language][field],
                f"[bold red]{TRANSLATION[ui_language]["none"]}[/]",
            )
        elif isinstance(value, list):
            joined = " ,".join(value)
            table.add_row(TRANSLATION[ui_language][field], joined)
        else:
            table.add_row(TRANSLATION[ui_language][field], value)

    console = Console()
    console.print(table)


@app.command()
def metadata(filename: Path):
    print(filename)


if __name__ == "__main__":
    app()
