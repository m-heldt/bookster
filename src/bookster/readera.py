from sqlmodel import create_engine, SQLModel, Field, Session
import zipfile
import re
import json

class ReadEraBackup(SQLModel, table=True):
    file_sha1: str = Field(primary_key=True)
    user_title: str | None = None
    user_authors: str | None = None
    user_langs: str | None = None
    user_series: str | None = None

def iter_readera_records(backup_path):
    with zipfile.ZipFile(backup_path) as backup:
        doc_files = [doc for doc in backup.namelist()
                     if re.fullmatch(r"docs_\d+\.json", doc)]

        for doc in doc_files:
            with backup.open(doc) as doc_file:
                doc_json = json.load(doc_file)

            for record in doc_json:
                fields = {
                    field:value for field, value in record["data"].items()
                    if field.startswith("user_")
                }
                if fields:
                    fields["file_sha1"] = record["uri"].removeprefix("sha-1:")
                    yield fields