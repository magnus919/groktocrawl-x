"""Deterministic application-owned passage preparation for ADR-0080."""

from dataclasses import dataclass

from .answer_units import SourcePassage
from .knowledge import text_digest

MAX_SOURCES = 8
MAX_PASSAGES = 32
MAX_PASSAGE_CHARACTERS = 4_000
MAX_SOURCE_BYTES = 120_000


@dataclass(frozen=True)
class RetainedSourceText:
    snapshot_id: str
    text: str


def prepare_source_passages(
    sources: tuple[RetainedSourceText, ...],
) -> tuple[SourcePassage, ...]:
    """Split exact retained text without normalization, ranking, or truncation."""

    if not 1 <= len(sources) <= MAX_SOURCES:
        raise ValueError("invalid retained source count")
    if len({source.snapshot_id for source in sources}) != len(sources):
        raise ValueError("retained snapshot identities must be distinct")
    if any(not source.snapshot_id or not source.text for source in sources):
        raise ValueError("retained source identity and text are required")
    if sum(len(source.text.encode()) for source in sources) > MAX_SOURCE_BYTES:
        raise ValueError("retained source byte budget exceeded")

    passages: list[SourcePassage] = []
    for source_index, source in enumerate(sources, 1):
        for start in range(0, len(source.text), MAX_PASSAGE_CHARACTERS):
            end = min(start + MAX_PASSAGE_CHARACTERS, len(source.text))
            quote = source.text[start:end]
            passages.append(
                SourcePassage(
                    passage_id=f"passage-{source_index}-{len(passages) + 1}",
                    snapshot_id=source.snapshot_id,
                    start=start,
                    end=end,
                    quote=quote,
                    quote_digest=text_digest(quote),
                )
            )
            if len(passages) > MAX_PASSAGES:
                raise ValueError("retained sources exceed passage-count budget")
    return tuple(passages)
