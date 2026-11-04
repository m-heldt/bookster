import typer
from pathlib import Path
from pprint import pp
from bookster.adapters import EPUBAdapter

app = typer.Typer()


@app.command()
def inspect(file_name: Path):
    print(f"Showing metadata of {file_name}:")
    epub_adapter = EPUBAdapter()
    metadata = epub_adapter.read_metadata(path=file_name)
    pp(metadata)


@app.command()
def metadata(filename: Path):
    print(filename)


if __name__ == "__main__":
    app()
