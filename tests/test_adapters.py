from pathlib import Path

import pikepdf

from bookster.adapters import PDFAdapter
from bookster.data import BookMetadata


# --- PDFAdapter.read_metadata ---


def test_pdf_read_metadata_handles_missing_xmp_fields(tmp_path: Path) -> None:
    path = tmp_path / "no-metadata.pdf"
    with pikepdf.new() as pdf:
        pdf.add_blank_page()
        pdf.save(path)

    assert PDFAdapter().read_metadata(path) == BookMetadata()


def test_pdf_read_metadata_normalizes_xmp_collections(tmp_path: Path) -> None:
    path = tmp_path / "with-metadata.pdf"
    with pikepdf.new() as pdf:
        pdf.add_blank_page()
        with pdf.open_metadata(set_pikepdf_as_editor=False, update_docinfo=False) as xmp:
            xmp["dc:creator"] = ["Zoe", "Alice"]
            xmp["dc:publisher"] = {"Z Press", "A Press"}
            xmp["dc:language"] = {"pl", "en"}
            xmp["dc:subject"] = {"Books"}
        pdf.save(path)

    metadata = PDFAdapter().read_metadata(path)

    assert [person.name for person in metadata.contributors] == ["Zoe", "Alice"]
    assert metadata.publisher == "A Press"
    assert metadata.languages == ["en", "pl"]
    assert metadata.subjects == ["Books"]
