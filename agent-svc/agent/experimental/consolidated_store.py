"""Atomic root-only consolidated fixture publication in the isolated database."""

import asyncio
from collections.abc import Mapping
from pathlib import Path
from uuid import UUID

from .canonical import MAX_BYTES, admit_canonical_json
from .checked_knowledge import CHECKED_SCHEMA, CheckedKnowledge, admit_checked_history
from .consolidated_journey import JourneyResult, RenderedReport
from .consolidated_storage_material import (
    RetainedConsolidated,
    StoredMaterial,
    context_digest,
)
from .context_sources import ResolvedContextSource
from .knowledge_context import KnowledgeContext
from .knowledge_execution import KnowledgeExecutionLedger
from .manifest_outputs import admit_render_manifest
from .publication_gate import _check_eligibility, prepare_publication
from .render_execution import RenderExecutionLedger
from .render_manifest import MANIFEST_SCHEMA, RenderManifest
from .research_import_store import ResearchImportStore
from .source_store import ROOT_QUOTA, Connection, StorageConflictError


class ConsolidatedStore(ResearchImportStore):
    async def migrate_consolidated(self) -> None:
        migration = (
            Path(__file__).with_name("migrations") / "010_consolidated_journey.sql"
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
            if version != [{"version": 9}]:
                raise StorageConflictError("consolidated migration requires schema 9")
            await conn.execute(migration.read_text(), prepare=False)

    @staticmethod
    async def _require_consolidated(conn: Connection) -> None:
        version = await (
            await conn.execute("SELECT version FROM research_staging.schema_version")
        ).fetchall()
        if version != [{"version": 10}]:
            raise StorageConflictError("consolidated schema unavailable")

    async def create_consolidated_root(
        self, scope: UUID, quota: int = ROOT_QUOTA
    ) -> UUID:
        if type(quota) is not int or not 0 < quota <= ROOT_QUOTA:
            raise ValueError("invalid consolidated root quota")
        async with self._transaction() as conn:
            await self._require_consolidated(conn)
            root = await self._insert_root(conn, scope, quota)
            await conn.execute(
                "UPDATE research_staging.roots SET revision_format='consolidated' WHERE scope_id=%s AND root_id=%s",
                (scope, root),
            )
            return root

    async def reserve_consolidated(
        self,
        scope: UUID,
        root: UUID,
        generation: int,
        size: int,
        context: KnowledgeContext,
    ) -> UUID:
        context = KnowledgeContext.model_validate_json(context.model_dump_json())
        if (
            context.parent_revision_id is not None
            or type(size) is not int
            or not 0 < size <= 5 * MAX_BYTES
        ):
            raise ValueError("invalid consolidated root reservation")
        digest = context_digest(context)
        async with self._transaction() as conn:
            await self._require_consolidated(conn)
            row = await self._lock(conn, scope, root)
            self._active(row, generation)
            if (
                row["revision_format"] != "consolidated"
                or row["current_consolidated"] is not None
            ):
                raise StorageConflictError("consolidated root already has a revision")
            if size > min(row["scope_free"], row["quota"] - row["charged"]):
                raise StorageConflictError("consolidated quota exhausted")
            await self._charge(conn, scope, root, size)
            operation = await (
                await conn.execute(
                    "INSERT INTO research_staging.consolidated_operations(scope_id,root_id,generation,context_digest,reserved) VALUES (%s,%s,%s,%s,%s) RETURNING operation_id",
                    (scope, root, generation, digest, size),
                )
            ).fetchone()
            await self._renew_staging(conn, scope, root)
            assert operation is not None
            return operation["operation_id"]

    async def commit_consolidated(
        self,
        scope: UUID,
        root: UUID,
        generation: int,
        operation: UUID,
        result: JourneyResult,
        bindings: Mapping[str, UUID],
        knowledge_owner: KnowledgeExecutionLedger,
        render_owner: RenderExecutionLedger,
    ) -> UUID:
        # Revalidate against physical staged sources, not the supplied candidate flag.
        material = StoredMaterial(self, scope, root, result, bindings)
        context = material.context
        candidate = await prepare_publication(
            result.manifest_bytes,
            scope_id=context.scope_id,
            research_id=context.research_id,
            revision_id=context.revision_id,
            artifact_set_id=result.candidate.admitted.manifest.artifact_set_id,
            prior=(),
            resolver=material,
            source_resolver=material,
            reviewers=tuple(
                {i.reviewer for i in material.knowledge.verification_inputs}
            ),
            knowledge_execution=knowledge_owner,
            render_execution=render_owner,
        )
        if not candidate.fixture_only or context.parent_revision_id is not None:
            raise StorageConflictError("only root fixture publications supported")
        admitted = candidate.admitted
        outputs = {
            a.layer: material.outputs[a.artifact_id].body
            for a in admitted.manifest.artifacts
        }
        size = (
            len(result.knowledge_bytes)
            + len(admitted.document.data)
            + sum(len(b) for b in outputs.values())
        )
        digest = admitted.document.digest
        async with self._transaction() as conn:
            await self._require_consolidated(conn)
            row = await self._lock(conn, scope, root)
            self._active(row, generation)
            op = await (
                await conn.execute(
                    "SELECT * FROM research_staging.consolidated_operations WHERE scope_id=%s AND root_id=%s AND operation_id=%s",
                    (scope, root, operation),
                )
            ).fetchone()
            if (
                row["revision_format"] != "consolidated"
                or op is None
                or op["generation"] != generation
                or op["state"] == "cancelled"
                or op["context_digest"] != context_digest(context)
            ):
                raise StorageConflictError("consolidated operation unavailable")
            pinned = StoredMaterial(self, scope, root, result, bindings, conn)
            for snapshot in context.snapshots:
                await pinned.resolve(snapshot.content_ref)
            if op["state"] == "committed":
                if op["input_digest"] != digest:
                    raise StorageConflictError("consolidated replay changed")
                return operation
            if row["current_consolidated"] is not None or size > op["reserved"]:
                raise StorageConflictError("consolidated parent or reservation changed")
            await conn.execute(
                "INSERT INTO research_staging.consolidated_publications(scope_id,root_id,operation_id,knowledge,knowledge_digest,manifest,manifest_digest,summary,analysis,dossier,fixture_only) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true)",
                (
                    scope,
                    root,
                    operation,
                    result.knowledge_bytes,
                    admitted.manifest.revision_digest,
                    admitted.document.data,
                    digest,
                    outputs["summary"],
                    outputs["analysis"],
                    outputs["dossier"],
                ),
            )
            for logical_id, snapshot_id in material.bindings.items():
                await conn.execute(
                    "INSERT INTO research_staging.consolidated_sources(scope_id,root_id,operation_id,logical_id,snapshot_id) VALUES (%s,%s,%s,%s,%s)",
                    (scope, root, operation, logical_id, snapshot_id),
                )
            await self._charge(conn, scope, root, size - op["reserved"])
            await conn.execute(
                "UPDATE research_staging.consolidated_operations SET state='committed',input_digest=%s WHERE scope_id=%s AND root_id=%s AND operation_id=%s",
                (digest, scope, root, operation),
            )
            await conn.execute(
                "UPDATE research_staging.roots SET current_consolidated=%s,published_at=now(),expires_at=now()+interval '30 days' WHERE scope_id=%s AND root_id=%s",
                (operation, scope, root),
            )
            task = asyncio.current_task()
            if task is not None and task.cancelling():
                raise asyncio.CancelledError
            knowledge_owner.check_bindings(admitted.knowledge)
            render_owner.check_bindings(admitted.manifest)
        return operation

    async def consolidated_receipt(
        self, scope: UUID, root: UUID, operation: UUID
    ) -> str | None:
        async with self._transaction(read=True) as conn:
            await self._require_consolidated(conn)
            row = await (
                await conn.execute(
                    "SELECT input_digest FROM research_staging.consolidated_operations WHERE scope_id=%s AND root_id=%s AND operation_id=%s AND state='committed'",
                    (scope, root, operation),
                )
            ).fetchone()
            return row["input_digest"] if row else None

    async def cancel_consolidated(
        self, scope: UUID, root: UUID, operation: UUID
    ) -> None:
        async with self._transaction() as conn:
            await self._require_consolidated(conn)
            await self._lock(conn, scope, root)
            row = await (
                await conn.execute(
                    "UPDATE research_staging.consolidated_operations SET state='cancelled' WHERE scope_id=%s AND root_id=%s AND operation_id=%s AND state='pending' RETURNING reserved",
                    (scope, root, operation),
                )
            ).fetchone()
            if row:
                await self._charge(conn, scope, root, -row["reserved"])

    async def read_consolidated(
        self, scope: UUID, root: UUID, operation: UUID
    ) -> RetainedConsolidated:
        async with self._transaction(read=True) as conn:
            await self._require_consolidated(conn)
            row = await (
                await conn.execute(
                    "SELECT p.*,o.context_digest FROM research_staging.consolidated_publications p JOIN research_staging.consolidated_operations o USING(scope_id,root_id,operation_id) JOIN research_staging.roots r USING(scope_id,root_id) WHERE p.scope_id=%s AND p.root_id=%s AND p.operation_id=%s AND NOT r.deleted AND r.expires_at>now() AND r.revision_format='consolidated' AND r.current_consolidated=p.operation_id AND o.state='committed' AND o.input_digest=p.manifest_digest",
                    (scope, root, operation),
                )
            ).fetchone()
            if row is None:
                raise StorageConflictError("consolidated publication unavailable")
            knowledge_document = admit_canonical_json(
                row["knowledge"], schema_version=CHECKED_SCHEMA
            )
            knowledge = CheckedKnowledge.model_validate_json(knowledge_document.data)
            manifest_document = admit_canonical_json(
                row["manifest"], schema_version=MANIFEST_SCHEMA
            )
            manifest = RenderManifest.model_validate_json(manifest_document.data)
            if (
                knowledge_document.data != row["knowledge"]
                or manifest_document.data != row["manifest"]
                or knowledge_document.digest != row["knowledge_digest"]
                or manifest_document.digest != row["manifest_digest"]
                or context_digest(knowledge.context) != row["context_digest"]
                or row["fixture_only"] is not True
            ):
                raise StorageConflictError("consolidated document integrity mismatch")
            links = await (
                await conn.execute(
                    "SELECT logical_id,snapshot_id FROM research_staging.consolidated_sources WHERE scope_id=%s AND root_id=%s AND operation_id=%s",
                    (scope, root, operation),
                )
            ).fetchall()
            bindings = {r["logical_id"]: r["snapshot_id"] for r in links}
            if set(bindings) != {s.snapshot_id for s in knowledge.context.snapshots}:
                raise StorageConflictError("consolidated retained sources incomplete")
            sources = []
            for snapshot in knowledge.context.snapshots:
                source = await self._read_source(
                    conn, scope, root, bindings[snapshot.snapshot_id]
                )
                sources.append(
                    ResolvedContextSource(
                        snapshot.content_ref,
                        source.body,
                        snapshot.normalization_version,
                        snapshot.media_type,
                    )
                )
            reports = tuple(RenderedReport(a, row[a.layer]) for a in manifest.artifacts)
            retained = RetainedConsolidated(
                row["knowledge"],
                row["manifest"],
                tuple(sources),
                reports,
                True,
                row["manifest_digest"],
            )
            material = StoredMaterial(self, scope, root, retained, bindings, conn)
            context = knowledge.context
            await admit_checked_history(
                row["knowledge"],
                prior=(),
                scope_id=context.scope_id,
                research_id=context.research_id,
                revision_id=context.revision_id,
                resolver=material,
                reviewers=tuple({i.reviewer for i in knowledge.verification_inputs}),
            )
            admitted = await admit_render_manifest(
                row["manifest"],
                scope_id=context.scope_id,
                research_id=context.research_id,
                revision_id=context.revision_id,
                artifact_set_id=manifest.artifact_set_id,
                resolver=material,
                reviewers=tuple({i.reviewer for i in manifest.audit_inputs}),
            )
            _check_eligibility(admitted)
            return retained
