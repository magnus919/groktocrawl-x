"""Bounded source-reported search metadata shared by every result path."""

from typing import Any

STRING_FIELDS = (
    "engine",
    "doi",
    "journal",
    "publisher",
    "editor",
    "pages",
    "number",
    "comments",
    "type",
    "pdf_url",
    "html_url",
    "publishedDate",
)
LIST_FIELDS = ("engines", "authors", "issn", "isbn", "tags")
METADATA_FIELDS = (*STRING_FIELDS, *LIST_FIELDS, "volume")


def search_metadata(source: dict[str, Any]) -> dict[str, Any]:
    """Keep compatible scholarly fields; never pass arbitrary upstream keys."""
    fields: dict[str, Any] = {}
    for key in STRING_FIELDS:
        value = source.get(key)
        if isinstance(value, str) and value and len(value) <= 2048:
            fields[key] = value
    for key in LIST_FIELDS:
        value = source.get(key)
        if (
            isinstance(value, list)
            and len(value) <= 64
            and all(isinstance(item, str) and len(item) <= 256 for item in value)
        ):
            fields[key] = sorted(set(value)) if key == "engines" else list(value)
    if "engines" not in fields and "engine" in fields:
        fields["engines"] = [fields["engine"]]
    volume = source.get("volume")
    if type(volume) in (str, int) and len(str(volume)) <= 256:
        fields["volume"] = volume
    return fields
