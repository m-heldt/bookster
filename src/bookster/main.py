import typer
from pathlib import Path

app = typer.Typer()


@app.command()
def inspect(file_name: Path):
    print(f"Showing metadata of {filename}:")


@app.command()
def metadata(filename: Path):
    print(filename)


if __name__ == "__main__":
    app()
