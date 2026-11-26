import typer
from pathlib import Path
from typing import Literal, Annotated
from sqlmodel import create_engine, Session, SQLModel
from rich import print as rprint
from rich.pretty import pprint
from rich.table import Table
from rich.console import Console
from rich.progress import Progress
from .adapters import get_adapter
from .data import BookMetadata, Role
from .readera import ReadEraBackup, iter_readera_records
from .llm import enrich_metadata_llm

app = typer.Typer()
metadata_app = typer.Typer()
app.add_typer(metadata_app, name="metadata", help="Perform actions with metadata.")
enrich_app = typer.Typer()
metadata_app.add_typer(enrich_app, name="enrich", help="Enrich book metadata with different sources.")


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
def inspect(book_path: str, ui_language: Literal["en", "pl"] = "en") -> None:
    book_path = Path(book_path)
    rprint(f"Showing the metadata of: {book_path.name}")
    adapter = get_adapter(book_path)
    metadata = adapter.read_metadata(path=book_path)

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
    name="import", help="Import user-edited metadata from ReadEra backup file."
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
            task = progress.add_task("Importing metadata from Readera...", total=None)
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

@enrich_app.command(
    name="llm"
)
def metadata_enrich_llm(book_path: str, ui_language: Literal["en", "pl"] = "en") -> None:
    book_path = Path(book_path)

    metadata_in_file = get_adapter(book_path).read_metadata(book_path)
    metadata_from_llm = enrich_metadata_llm(book_path)
    
    table = Table(show_header=True)
    
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column("File")
    table.add_column("LLM")
    
    for field in BookMetadata.model_fields:
        value_file = getattr(metadata_in_file, field)
        value_llm = getattr(metadata_from_llm, field)

        if field == "contributors":
            authors_file = [
                contributor.name
                for contributor in value_file
                if contributor.role == Role.AUTHOR
            ]
            authors_llm = [
                contributor.name
                for contributor in value_llm
                if contributor.role == Role.AUTHOR
            ]
            table.add_row(TRANSLATION[ui_language]["author"], ", ".join(authors_file), ", ".join(authors_llm))
        elif value_file is None or not value_file:
            if value_llm is None or not value_llm:
                value_llm = f"[bold red]{TRANSLATION[ui_language]["none"]}[/]"
            
            table.add_row(
                TRANSLATION[ui_language][field],
                f"[bold red]{TRANSLATION[ui_language]["none"]}[/]",
                str(value_llm)
            )
        elif isinstance(value_file, list) and isinstance(value_llm, list):
            joined_file = " ,".join(value_file)
            joined_llm = " ,".join(value_llm)
            table.add_row(TRANSLATION[ui_language][field], joined_file, joined_llm)
        else:
            table.add_row(TRANSLATION[ui_language][field], str(value_file), str(value_llm))

    console = Console()
    console.print(table)

    raise typer.Exit(0)


if __name__ == "__main__":
    app()
