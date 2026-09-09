"""Fail-open pgvector shadow storage for semantic-service experiments.

Qdrant remains authoritative. This module never selects served results and
records failures through its caller instead of changing request outcomes.
"""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


def _vector_literal(vector: Sequence[float]) -> str:
    return "[" + ",".join(format(float(value), ".17g") for value in vector) + "]"


@dataclass(frozen=True)
class ShadowConfig:
    mode: str
    dsn: str
    schema: str
    table: str
    sample_rate: float
    score_tolerance: float

    @property
    def enabled(self) -> bool:
        return self.mode == "shadow_pgvector"

    @classmethod
    def from_env(cls) -> ShadowConfig:
        mode = os.getenv("VECTOR_STORE_MODE", "qdrant").strip().lower()
        if mode not in {"qdrant", "shadow_pgvector"}:
            raise ValueError("VECTOR_STORE_MODE must be qdrant or shadow_pgvector")
        dsn = os.getenv("PGVECTOR_SHADOW_DSN", "").strip()
        if mode == "shadow_pgvector" and not dsn:
            raise ValueError("PGVECTOR_SHADOW_DSN is required in shadow_pgvector mode")
        sample_rate = float(os.getenv("PGVECTOR_SHADOW_SAMPLE_RATE", "0.1"))
        if not 0.0 <= sample_rate <= 1.0:
            raise ValueError("PGVECTOR_SHADOW_SAMPLE_RATE must be between 0 and 1")
        tolerance = float(os.getenv("PGVECTOR_SHADOW_SCORE_TOLERANCE", "0.0001"))
        if tolerance < 0:
            raise ValueError("PGVECTOR_SHADOW_SCORE_TOLERANCE must be non-negative")
        return cls(
            mode=mode,
            dsn=dsn,
            schema="groktocrawl_x_semantic_shadow",
            table="pages",
            sample_rate=sample_rate,
            score_tolerance=tolerance,
        )


@dataclass(frozen=True)
class ShadowSearchResult:
    point_id: int
    url: str
    title: str
    score: float


@dataclass(frozen=True)
class ShadowComparison:
    matches: bool
    authoritative_ids: tuple[int, ...]
    shadow_ids: tuple[int, ...]
    maximum_score_delta: float | None


def compare_results(
    authoritative: Sequence[tuple[int, float]],
    shadow: Sequence[ShadowSearchResult],
    *,
    score_tolerance: float,
) -> ShadowComparison:
    authoritative_ids = tuple(point_id for point_id, _ in authoritative)
    shadow_ids = tuple(result.point_id for result in shadow)
    deltas = [
        abs(authoritative_score - shadow_result.score)
        for (authoritative_id, authoritative_score), shadow_result in zip(
            authoritative, shadow, strict=False
        )
        if authoritative_id == shadow_result.point_id
    ]
    maximum_delta = max(deltas) if deltas else None
    matches = (
        authoritative_ids == shadow_ids
        and len(authoritative) == len(shadow)
        and maximum_delta is not None
        and maximum_delta <= score_tolerance
    ) or (not authoritative and not shadow)
    return ShadowComparison(
        matches=matches,
        authoritative_ids=authoritative_ids,
        shadow_ids=shadow_ids,
        maximum_score_delta=maximum_delta,
    )


class PgvectorShadowStore:
    """Small synchronous adapter invoked off the semantic-service event loop."""

    def __init__(self, config: ShadowConfig, dimension: int) -> None:
        self.config = config
        self.dimension = dimension
        self._connection: Any | None = None
        self._lock = threading.Lock()

    def _connect(self) -> Any:
        if self._connection is None:
            import psycopg

            self._connection = psycopg.connect(self.config.dsn, autocommit=True)
        return self._connection

    def ensure_schema(self) -> None:
        if not self.config.enabled:
            return
        with self._lock:
            connection = self._connect()
            connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
            connection.execute(f"CREATE SCHEMA IF NOT EXISTS {self.config.schema}")
            connection.execute(
                f"""CREATE TABLE IF NOT EXISTS {self.config.schema}.{self.config.table} (
                    point_id bigint PRIMARY KEY,
                    url text NOT NULL,
                    title text NOT NULL,
                    embedding vector({self.dimension}) NOT NULL,
                    model text NOT NULL,
                    payload jsonb NOT NULL,
                    deleted boolean NOT NULL DEFAULT false,
                    updated_at timestamptz NOT NULL DEFAULT now()
                )"""
            )
            connection.execute(
                f"CREATE INDEX IF NOT EXISTS {self.config.table}_embedding_hnsw "
                f"ON {self.config.schema}.{self.config.table} "
                "USING hnsw (embedding vector_cosine_ops)"
            )

    def upsert(
        self,
        *,
        point_id: int,
        url: str,
        title: str,
        vector: Sequence[float],
        model: str,
        payload: Mapping[str, Any],
    ) -> None:
        if len(vector) != self.dimension:
            raise ValueError(
                "shadow vector dimension does not match configured dimension"
            )
        with self._lock:
            connection = self._connect()
            connection.execute(
                f"""INSERT INTO {self.config.schema}.{self.config.table}
                    (point_id, url, title, embedding, model, payload, deleted, updated_at)
                    VALUES (%s, %s, %s, %s::vector, %s, %s::jsonb, false, now())
                    ON CONFLICT (point_id) DO UPDATE SET
                      url=EXCLUDED.url, title=EXCLUDED.title,
                      embedding=EXCLUDED.embedding, model=EXCLUDED.model,
                      payload=EXCLUDED.payload, deleted=false, updated_at=now()""",
                (
                    point_id,
                    url,
                    title,
                    _vector_literal(vector),
                    model,
                    json.dumps(dict(payload), separators=(",", ":"), sort_keys=True),
                ),
            )

    def delete(self, point_id: int) -> None:
        with self._lock:
            self._connect().execute(
                f"""UPDATE {self.config.schema}.{self.config.table}
                SET deleted=true, updated_at=now() WHERE point_id=%s""",
                (point_id,),
            )

    def search(
        self, vector: Sequence[float], *, model: str, limit: int
    ) -> list[ShadowSearchResult]:
        if len(vector) != self.dimension:
            raise ValueError(
                "shadow query dimension does not match configured dimension"
            )
        with self._lock:
            rows = (
                self._connect()
                .execute(
                    f"""SELECT point_id, url, title,
                    1 - (embedding <=> %s::vector) AS score
                FROM {self.config.schema}.{self.config.table}
                WHERE model=%s AND deleted=false
                ORDER BY embedding <=> %s::vector, point_id
                LIMIT %s""",
                    (_vector_literal(vector), model, _vector_literal(vector), limit),
                )
                .fetchall()
            )
        return [
            ShadowSearchResult(int(row[0]), str(row[1]), str(row[2]), float(row[3]))
            for row in rows
        ]

    def close(self) -> None:
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None
