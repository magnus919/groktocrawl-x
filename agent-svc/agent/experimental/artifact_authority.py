"""PostgreSQL authority for complete experimental research artifact sets."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from .source_store import SourceStore, StorageConflictError

MAX_MANIFEST_BYTES = 1024 * 1024
MAX_ARTIFACT_BYTES = 10 * 1024 * 1024
MAX_SET_BYTES = 32 * 1024 * 1024
RETAINED_LAYERS = ("summary", "analysis", "dossier")


@dataclass(frozen=True)
class ArtifactMaterial:
    artifact_id: str
    layer: str
    body: bytes
    content_digest: str


@dataclass(frozen=True)
class RetainedArtifactSet:
    scope_id: UUID
    research_id: UUID
    run_id: UUID
    artifact_set_id: UUID
    manifest: bytes
    manifest_digest: str
    set_digest: str
    artifacts: tuple[ArtifactMaterial, ...]


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def artifact_set_digest(
    manifest_digest: str, artifacts: tuple[ArtifactMaterial, ...]
) -> str:
    material = [f"manifest:{manifest_digest}"]
    material.extend(
        f"{item.layer}:{item.artifact_id}:{item.content_digest}"
        for item in sorted(
            artifacts, key=lambda value: (value.layer, value.artifact_id)
        )
    )
    return _sha256("\n".join(material).encode("utf-8"))


class ArtifactAuthority(SourceStore):
    """Atomic, scoped storage boundary; callers establish scope authorization."""

    async def migrate_artifact_authority(self) -> None:
        migration = (
            Path(__file__).with_name("migrations")
            / "013_research_artifact_authority.sql"
        )
        async with self._transaction(bootstrap=True) as conn:
            await conn.execute(
                "LOCK TABLE research_staging.schema_version IN ACCESS EXCLUSIVE MODE"
            )
            version = await (
                await conn.execute(
                    "SELECT version FROM research_staging.schema_version"
                )
            ).fetchall()
            if version != [{"version": 12}]:
                raise StorageConflictError(
                    "artifact authority migration requires schema 12"
                )
            await conn.execute(migration.read_text(), prepare=False)

    @staticmethod
    def _validate(
        manifest: bytes, artifacts: Mapping[str, tuple[str, bytes]]
    ) -> tuple[str, tuple[ArtifactMaterial, ...], str, int]:
        if (
            not isinstance(manifest, bytes)
            or not 0 < len(manifest) <= MAX_MANIFEST_BYTES
        ):
            raise ValueError("manifest byte limit exceeded")
        if set(artifacts) != set(RETAINED_LAYERS):
            raise ValueError("complete summary, analysis, and dossier set required")
        retained = []
        for layer in RETAINED_LAYERS:
            artifact_id, body = artifacts[layer]
            if not isinstance(artifact_id, str) or not 0 < len(artifact_id) <= 200:
                raise ValueError("invalid artifact identity")
            if not isinstance(body, bytes) or not 0 < len(body) <= MAX_ARTIFACT_BYTES:
                raise ValueError("artifact byte limit exceeded")
            retained.append(ArtifactMaterial(artifact_id, layer, body, _sha256(body)))
        values = tuple(retained)
        manifest_digest = _sha256(manifest)
        total = len(manifest) + sum(len(item.body) for item in values)
        if total > MAX_SET_BYTES:
            raise ValueError("artifact set byte limit exceeded")
        return (
            manifest_digest,
            values,
            artifact_set_digest(manifest_digest, values),
            total,
        )

    async def commit(
        self,
        scope: UUID,
        research: UUID,
        run: UUID,
        artifact_set: UUID,
        manifest: bytes,
        artifacts: Mapping[str, tuple[str, bytes]],
    ) -> RetainedArtifactSet:
        manifest_digest, retained, set_digest, total = self._validate(
            manifest, artifacts
        )
        async with self._transaction() as conn:
            version = await (
                await conn.execute(
                    "SELECT version FROM research_staging.schema_version"
                )
            ).fetchall()
            if version != [{"version": 13}]:
                raise StorageConflictError("artifact authority schema unavailable")
            prior = await (
                await conn.execute(
                    "SELECT research_id,artifact_set_id,set_digest,deleted FROM research_staging.research_artifact_sets WHERE scope_id=%s AND run_id=%s FOR UPDATE",
                    (scope, run),
                )
            ).fetchone()
            if prior is not None:
                if prior["deleted"] or (
                    prior["research_id"],
                    prior["artifact_set_id"],
                    prior["set_digest"],
                ) != (research, artifact_set, set_digest):
                    raise StorageConflictError("artifact set replay changed")
                return await self._read(conn, scope, research)
            await conn.execute(
                "INSERT INTO research_staging.research_artifact_sets(scope_id,research_id,run_id,artifact_set_id,manifest,manifest_digest,set_digest,total_bytes) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    scope,
                    research,
                    run,
                    artifact_set,
                    manifest,
                    manifest_digest,
                    set_digest,
                    total,
                ),
            )
            for item in retained:
                await conn.execute(
                    "INSERT INTO research_staging.research_artifacts(scope_id,research_id,artifact_id,layer,body,content_digest) VALUES (%s,%s,%s,%s,%s,%s)",
                    (
                        scope,
                        research,
                        item.artifact_id,
                        item.layer,
                        item.body,
                        item.content_digest,
                    ),
                )
            return RetainedArtifactSet(
                scope,
                research,
                run,
                artifact_set,
                manifest,
                manifest_digest,
                set_digest,
                retained,
            )

    async def _read(self, conn, scope: UUID, research: UUID) -> RetainedArtifactSet:
        row = await (
            await conn.execute(
                "SELECT * FROM research_staging.research_artifact_sets WHERE scope_id=%s AND research_id=%s AND NOT deleted AND expires_at>now()",
                (scope, research),
            )
        ).fetchone()
        if row is None:
            raise StorageConflictError("artifact set unavailable")
        children = await (
            await conn.execute(
                "SELECT artifact_id,layer,body,content_digest FROM research_staging.research_artifacts WHERE scope_id=%s AND research_id=%s ORDER BY CASE layer WHEN 'summary' THEN 1 WHEN 'analysis' THEN 2 WHEN 'dossier' THEN 3 END,artifact_id",
                (scope, research),
            )
        ).fetchall()
        manifest = bytes(row["manifest"])
        artifacts = tuple(
            ArtifactMaterial(
                value["artifact_id"],
                value["layer"],
                bytes(value["body"]),
                value["content_digest"],
            )
            for value in children
        )
        if (
            {item.layer for item in artifacts} != set(RETAINED_LAYERS)
            or _sha256(manifest) != row["manifest_digest"]
            or any(_sha256(item.body) != item.content_digest for item in artifacts)
            or artifact_set_digest(row["manifest_digest"], artifacts)
            != row["set_digest"]
        ):
            raise StorageConflictError("artifact set integrity mismatch")
        return RetainedArtifactSet(
            scope,
            research,
            row["run_id"],
            row["artifact_set_id"],
            manifest,
            row["manifest_digest"],
            row["set_digest"],
            artifacts,
        )

    async def read(self, scope: UUID, research: UUID) -> RetainedArtifactSet:
        async with self._transaction(read=True) as conn:
            return await self._read(conn, scope, research)

    async def read_run(self, scope: UUID, run: UUID) -> RetainedArtifactSet:
        async with self._transaction(read=True) as conn:
            row = await (
                await conn.execute(
                    "SELECT research_id FROM research_staging.research_artifact_sets WHERE scope_id=%s AND run_id=%s AND NOT deleted AND expires_at>now()",
                    (scope, run),
                )
            ).fetchone()
            if row is None:
                raise StorageConflictError("artifact set unavailable")
            return await self._read(conn, scope, row["research_id"])

    async def delete(self, scope: UUID, research: UUID) -> None:
        async with self._transaction() as conn:
            row = await (
                await conn.execute(
                    "UPDATE research_staging.research_artifact_sets SET deleted=true,manifest=NULL WHERE scope_id=%s AND research_id=%s AND NOT deleted RETURNING research_id",
                    (scope, research),
                )
            ).fetchone()
            if row is None:
                raise StorageConflictError("artifact set unavailable")
            await conn.execute(
                "DELETE FROM research_staging.research_artifacts WHERE scope_id=%s AND research_id=%s",
                (scope, research),
            )
