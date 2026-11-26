from openai import OpenAI
import os
from pathlib import Path
from .data import BookMetadata
from .adapters import get_adapter

_MODEL = "openai/gpt-6-luna"

_INSTRUCTIONS = """
You are given ebook metadata in a structured form, a few first pages and a few excerpts.
Your job is to fill the fields that are lacking information and correct inaccuracies.
Use `<first name> <last name>` format for contributors (Person field name). Fill in family_name and given_names if reasonably certain.
Prepare a description of ~300 words. Do not include any sources/source links in the description.
Do not invent missing information.
"""


def compose_payload(metadata: BookMetadata, front_matter: list[str], excerpts: list[str]):
    return f"""Metadata: 
    {metadata.model_dump_json(indent=2)}

    First five pages:
    {front_matter}

    Excerpts:
    {excerpts}
    """


def enrich_metadata_llm(path: Path, model=_MODEL) -> BookMetadata:
    client = OpenAI(
        base_url=f"{os.environ["BIFROST_BASE_URL"]}",
        api_key=os.environ["BIFROST_API_KEY"],
    )

    adapter = get_adapter(path)
    metadata = adapter.read_metadata(path)
    front_matter = adapter.get_front_matter(path)
    excerpts = adapter.get_excerpts(path)

    response = client.responses.parse(
        model=model,
        instructions=_INSTRUCTIONS,
        input=compose_payload(
            metadata,
            front_matter,
            excerpts,
        ),
        tools=[{"type": "web_search"}],
        tool_choice="required",
        text_format=BookMetadata,
    )

    return response.output_parsed
