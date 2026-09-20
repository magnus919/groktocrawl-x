"""Tests for error propagation in the find-similar qdrant path.

Covers ``agent-svc/agent/research/similar.py:_run_find_similar_qdrant``:
when semantic-svc fails for the vector search (503 index unavailable,
500 internal error, timeout on a slow backend, or connection error),
find-similar MUST raise the typed ``SemanticError`` (HTTP 502,
``SEMANTIC_SERVICE_ERROR``) instead of masking the failure as an empty
success result (issue #588).

The scrape-stage short-circuit is preserved: a failed scrape of the
query URL still degrades to ``[]`` without ever calling the semantic
service.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from agent.exceptions import GroktoCrawlError, SemanticError
from agent.research.similar import _run_find_similar_qdrant


class _FakeScraper:
    def __init__(self):
        self.closed = False

    async def scrape(self, url):
        return {
            "success": True,
            "data": {
                "markdown": "# Herbs\nHydroponic herb gardening tips.",
                "metadata": {"title": "Herb Garden"},
            },
        }

    async def close(self):
        self.closed = True


class _FakeSemantic:
    def __init__(self, search_vector, rerank=None):
        self._search_vector = search_vector
        self._rerank = rerank
        self.search_vector_calls: list[tuple[str, int]] = []
        self.closed = False

    async def search_vector(self, query, limit=5):
        self.search_vector_calls.append((query, limit))
        return await self._search_vector(query, limit)

    async def rerank(self, query, documents, top_k=5):
        if self._rerank is None:
            return [
                {"index": index, "score": 1.0 - index / 10}
                for index in range(min(top_k, len(documents)))
            ]
        return await self._rerank(query, documents, top_k)

    async def close(self):
        self.closed = True


def _mock_http_status_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "http://semantic-svc:8003/search/vector")
    response = httpx.Response(status, request=request)
    return httpx.HTTPStatusError("error", request=request, response=response)


async def _run(scraper=None, semantic=None):
    """Invoke _run_find_similar_qdrant with patched clients."""
    with (
        patch(
            "agent.research.similar.ScraperClient",
            return_value=scraper or _FakeScraper(),
        ),
        patch("agent.semantic_client.SemanticClient", return_value=semantic),
    ):
        return await _run_find_similar_qdrant(
            url="https://example.com/herbs",
            limit=5,
            scraper_url="http://scraper-svc:8001",
            semantic_url="http://semantic-svc:8003",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [503, 500])
async def test_qdrant_http_status_error_raises_semantic_error(status):
    """An upstream HTTP error status from semantic-svc raises SemanticError."""
    semantic = _FakeSemantic(AsyncMock(side_effect=_mock_http_status_error(status)))

    with pytest.raises(SemanticError) as exc_info:
        await _run(semantic=semantic)

    assert exc_info.value.status_code == 502
    assert exc_info.value.error_code == "SEMANTIC_SERVICE_ERROR"
    # The detail identifies the upstream HTTP condition.
    assert str(status) in exc_info.value.detail


@pytest.mark.asyncio
async def test_qdrant_timeout_raises_semantic_error():
    """A timeout (slow backend) raises SemanticError naming the exception type."""
    request = httpx.Request("POST", "http://semantic-svc:8003/search/vector")
    semantic = _FakeSemantic(
        AsyncMock(side_effect=httpx.ReadTimeout("timed out", request=request))
    )

    with pytest.raises(SemanticError) as exc_info:
        await _run(semantic=semantic)

    assert exc_info.value.status_code == 502
    assert exc_info.value.error_code == "SEMANTIC_SERVICE_ERROR"
    detail = exc_info.value.detail
    assert "ReadTimeout" in detail or "timeout" in detail.lower()


@pytest.mark.asyncio
async def test_qdrant_connect_error_raises_semantic_error():
    """An unreachable semantic-svc (connection error) raises SemanticError."""
    request = httpx.Request("POST", "http://semantic-svc:8003/search/vector")
    semantic = _FakeSemantic(
        AsyncMock(side_effect=httpx.ConnectError("connection refused", request=request))
    )

    with pytest.raises(SemanticError) as exc_info:
        await _run(semantic=semantic)

    assert isinstance(exc_info.value, GroktoCrawlError)
    assert exc_info.value.status_code == 502
    assert exc_info.value.error_code == "SEMANTIC_SERVICE_ERROR"
    assert "ConnectError" in exc_info.value.detail


@pytest.mark.asyncio
async def test_scrape_failure_short_circuits_before_search_vector():
    """A failed scrape returns [] without calling search_vector (no error)."""
    semantic = _FakeSemantic(
        AsyncMock(side_effect=AssertionError("search_vector must not be called"))
    )

    class _FailingScraper:
        async def scrape(self, url):
            return {"success": False, "error": "scrape failed"}

        async def close(self):
            pass

    results = await _run(scraper=_FailingScraper(), semantic=semantic)

    assert results == []
    assert semantic.search_vector_calls == []


@pytest.mark.asyncio
async def test_empty_markdown_short_circuits_before_search_vector():
    """Empty scraped markdown returns [] without calling search_vector."""
    semantic = _FakeSemantic(
        AsyncMock(side_effect=AssertionError("search_vector must not be called"))
    )

    class _BlankScraper:
        async def scrape(self, url):
            return {"success": True, "data": {"markdown": "", "metadata": {}}}

        async def close(self):
            pass

    results = await _run(scraper=_BlankScraper(), semantic=semantic)

    assert results == []
    assert semantic.search_vector_calls == []


@pytest.mark.asyncio
async def test_qdrant_success_returns_results():
    """A healthy vector search returns mapped results unchanged."""

    async def _ok(query, limit):
        return [{"url": "https://a.com", "title": "A", "content": "content A"}]

    semantic = _FakeSemantic(_ok)

    results = await _run(semantic=semantic)

    assert results == [
        {
            "url": "https://a.com",
            "title": "A",
            "description": "content A",
            "score": None,
            "confidence": "unknown",
            "raw_rank": 1,
            "metadata_complete": True,
            "provenance": {
                "source": "local_vector_index",
                "indexed_at": None,
                "index_freshness": "unavailable",
                "ranking_method": "vector_cosine",
            },
            "rank": 1,
        }
    ]


@pytest.mark.asyncio
async def test_qdrant_rerank_pool_is_bounded_to_ten():
    async def _search(query, limit):
        assert limit == 10
        return [
            {
                "url": f"https://example.com/{index}",
                "title": f"Candidate {index}",
                "description": f"Document {index}",
                "score": 0.9 - index / 100,
            }
            for index in range(10)
        ]

    async def _rerank(query, documents, top_k):
        assert len(query) <= 900
        assert len(documents) == 10
        assert top_k == 10
        return [
            {"index": index, "score": index / 10}
            for index in reversed(range(10))
        ]

    semantic = _FakeSemantic(_search, _rerank)
    with (
        patch("agent.research.similar.ScraperClient", return_value=_FakeScraper()),
        patch("agent.semantic_client.SemanticClient", return_value=semantic),
    ):
        results = await _run_find_similar_qdrant(
            url="https://query.example.com/herbs",
            limit=5,
            scraper_url="http://scraper-svc:8001",
            semantic_url="http://semantic-svc:8003",
        )

    assert [item["raw_rank"] for item in results] == [10, 9, 8, 7, 6]
    assert [item["rank"] for item in results] == [1, 2, 3, 4, 5]
    assert results[0]["provenance"]["ranking_method"] == "cross_encoder_bounded"
    assert results[0]["provenance"]["candidate_pool_size"] == 10
