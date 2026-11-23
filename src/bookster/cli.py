import typer
from pathlib import Path
from rich import print as rprint
from rich.pretty import pprint
from rich.table import Table
from rich.console import Console
from rich.progress import Progress
from bookster.adapters import EPUBAdapter
from bookster.data import BookMetadata, Role
from typing import Literal, Annotated
from sqlmodel import create_engine, Session, SQLModel
from .readera import ReadEraBackup, iter_readera_records

app = typer.Typer()
metadata_app = typer.Typer()
app.add_typer(metadata_app, name="metadata", help="Perform actions with metadata.")


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


@app.command(help="Show ebook metadata.")
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

    raise typer.Exit(0)


@metadata_app.command(
    name="import", help="Import user-edited metadata from ReadEra backup file"
)
def metadata_import(backup_path: Path, force: bool = False) -> None:
    BATCH_SIZE = 500
    DB_PATH = "readera.db"

    if force and Path(DB_PATH).exists():
        Path(DB_PATH).unlink()
    elif Path(DB_PATH).exists():
        rprint("ReadEra database already exists.")
        rprint("Use with --force to overwrite the database file.")
        rprint("Exiting now...")
        raise typer.Exit(0)



    engine = create_engine(f"sqlite:///{DB_PATH}")

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        readera_records = iter_readera_records(backup_path)
        batch = []
        processed = 0
        with Progress() as progress:
            task = progress.add_task(
                "Importing metadata from Readera...",
                total=None
            )
            for record in readera_records:
                batch.append(ReadEraBackup(**record))
                if len(batch) == BATCH_SIZE:
                    session.add_all(batch)
                    batch.clear()
                    progress.advance(task, BATCH_SIZE)
                    processed += BATCH_SIZE
        if batch:
            session.add_all(batch)
            session.commit()
            processed += len(batch)
            rprint(f"{processed} records were imported.")

        raise typer.Exit(0)


if __name__ == "__main__":
    app()
