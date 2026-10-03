"""Source metadata survives acquisition without new network/model work."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from agent.models import ContentsOptions, SearchRequest, SearchResult
from agent.research.hybrid import _collect_candidates
from agent.search_metadata import search_metadata
from agent.searxng_client import SearchHealth, SearXNGClient

SOURCE = {
    "url": "https://example.test/paper",
    "title": "Public fixture",
    "description": "Public scholarly snippet",
    "engine": "brave",
    "engines": ["semanticscholar", "brave"],
    "doi": "10.1234/fixture",
    "authors": ["A. Author"],
    "journal": "Fixture Journal",
    "comments": "Retracted Publication",
}


def assert_metadata(row):
    for key, value in search_metadata(SOURCE).items():
        assert (set(row[key]) == set(value)) if key == "engines" else row[key] == value
    assert isinstance(row["url"], str)


def test_public_model_retains_metadata_and_legacy_missing_shape():
    assert_metadata(SearchResult(**SOURCE).model_dump())
    legacy = SearchResult(url=SOURCE["url"], title=SOURCE["title"]).model_dump()
    assert "engine" not in legacy and "doi" not in legacy


def test_malformed_metadata_is_omitted_and_single_engine_fallback():
    assert search_metadata({"engines": "bad", "doi": ["bad"], "url": "bad"}) == {}
    assert search_metadata({"engine": "brave"}) == {
        "engine": "brave",
        "engines": ["brave"],
    }


@pytest.mark.asyncio
async def test_client_retains_optional_fields_without_extra_requests():
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(
            200, json={"results": [{**SOURCE, "content": SOURCE["description"]}]}
        )

    client = SearXNGClient("https://search.example.test")
    await client._client.aclose()
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        rows, _ = await client.search("public query")
    finally:
        await client.close()
    assert_metadata(rows[0])
    assert len(calls) == 1


def test_hybrid_blend_keeps_web_metadata_when_vector_matches():
    _, _, candidates = _collect_candidates(
        [SOURCE], [{"url": SOURCE["url"], "title": "Vector", "score": 0.9}]
    )
    assert_metadata(next(iter(candidates.values())))


@pytest.mark.asyncio
@pytest.mark.parametrize("contents", [None, ContentsOptions(summary=True)])
async def test_fast_and_enriched_routes_keep_metadata(monkeypatch, contents):
    from agent.routes.search import search

    searcher = SimpleNamespace(
        search=AsyncMock(return_value=([SOURCE], SearchHealth())), close=AsyncMock()
    )
    scraper = SimpleNamespace(
        scrape=AsyncMock(
            return_value={"success": True, "data": {"markdown": "Public evidence"}}
        ),
        close=AsyncMock(),
    )
    llm = SimpleNamespace(
        generate=AsyncMock(return_value="Fixture summary"), close=AsyncMock()
    )
    for target, value in [
        ("agent.searxng_client.SearXNGClient", searcher),
        ("agent.scraper_client.ScraperClient", scraper),
        ("agent.llm.LLMClient", llm),
    ]:
        monkeypatch.setattr(target, lambda *_a, _value=value, **_kw: _value)
    state = SimpleNamespace(
        searxng_url="fixture",
        scraper_url="fixture",
        semantic_url="fixture",
        llm_base_url="fixture",
        llm_api_key="",
        llm_model="fixture",
    )
    response = await search(
        SimpleNamespace(app=SimpleNamespace(state=state)),
        SearchRequest(query="Public query", contents=contents),
    )
    assert_metadata(response.data["web"][0])
    assert searcher.search.await_count == 1


@pytest.mark.asyncio
async def test_deep_search_preserves_metadata(monkeypatch):
    from agent.research.search import run_deep_search

    searcher = SimpleNamespace(
        search=AsyncMock(return_value=([SOURCE], SearchHealth())), close=AsyncMock()
    )
    llm = SimpleNamespace(generate=AsyncMock(return_value="[]"), close=AsyncMock())
    monkeypatch.setattr(
        "agent.research.search.SearXNGClient", lambda *_a, **_kw: searcher
    )
    monkeypatch.setattr("agent.research.search.LLMClient", lambda *_a, **_kw: llm)
    response = await run_deep_search("Public query", 10, llm_model="fixture")
    assert_metadata(response["results"][0].model_dump())
