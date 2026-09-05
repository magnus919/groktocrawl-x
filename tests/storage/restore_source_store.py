"""Synthetic restore rehearsal, never an operator recovery or import command."""

import asyncio
import json
import sys
from uuid import UUID

import psycopg
from agent.experimental.source_store import SourceStore, StorageConflictError

SCOPE = UUID("37249300-d005-4f26-813c-3a6ecc9f54cc")
DELETED_BODY = b"Fixture evidence deleted AFTER the backup."
RETAINED_BODY = b"Fixture evidence retained across the backup."


async def rows(query, params=()):
    async with await psycopg.AsyncConnection.connect() as conn:
        return await (await conn.execute(query, params)).fetchall()


async def seed():
    store = SourceStore()
    await store.provision_scope(SCOPE)
    for body in (DELETED_BODY, RETAINED_BODY):
        root = await store.create_root(SCOPE)
        operation = await store.reserve(SCOPE, root, 1, 1000)
        await store.commit_source(
            SCOPE, root, 1, operation, body, "https://example.test/restore"
        )
    print("Seeded bounded restore fixtures")


async def marker():
    result = await rows(
        "SELECT s.root_id,s.snapshot_id FROM research_staging.snapshots s "
        "JOIN research_staging.blobs b ON b.scope_id=s.scope_id AND b.digest=s.body_digest "
        "WHERE s.scope_id=%s AND b.body=%s",
        (SCOPE, DELETED_BODY),
    )
    if len(result) != 1:
        raise ValueError("expected one pre-deletion restore fixture")
    return result[0]


async def delete_and_inventory():
    root, _ = await marker()
    await SourceStore().delete_root(SCOPE, root)
    deleted = await rows(
        "SELECT scope_id,root_id FROM research_staging.roots WHERE deleted ORDER BY scope_id,root_id"
    )
    print(
        json.dumps(
            {
                "schema_version": "fixture-deletion-inventory/1",
                "deleted": [[str(scope), str(root)] for scope, root in deleted],
            }
        )
    )


async def verify():
    # This DB has no serving endpoint. Stay quarantined on absent/bad inventory.
    raw = sys.stdin.buffer.read(1024 * 1024 + 1)
    if not raw or len(raw) > 1024 * 1024:
        raise ValueError("bounded current deletion inventory required")
    inventory = json.loads(raw)
    if (
        set(inventory) != {"schema_version", "deleted"}
        or inventory["schema_version"] != "fixture-deletion-inventory/1"
    ):
        raise ValueError("unsupported deletion inventory")
    deleted = {(UUID(scope), UUID(root)) for scope, root in inventory["deleted"]}
    root, snapshot = await marker()
    if (SCOPE, root) not in deleted:
        raise ValueError(
            "post-backup deletion history missing; keep restore quarantined"
        )
    store = SourceStore()
    # Prove this is the old backup, not an accidentally fresh post-deletion copy.
    if (await store.read_source(SCOPE, root, snapshot)).body != DELETED_BODY:
        raise AssertionError("backup fixture changed")
    for scope, deleted_root in deleted:
        existing = await rows(
            "SELECT 1 FROM research_staging.roots WHERE scope_id=%s AND root_id=%s",
            (scope, deleted_root),
        )
        if existing:
            await store.delete_root(scope, deleted_root)
    try:
        await store.read_source(SCOPE, root, snapshot)
    except StorageConflictError:
        pass
    else:
        raise AssertionError("deleted evidence was re-exposed")
    retained = await rows(
        "SELECT s.scope_id,s.root_id,s.snapshot_id FROM research_staging.snapshots s "
        "JOIN research_staging.roots r USING(scope_id,root_id) WHERE NOT r.deleted AND r.expires_at>now()"
    )
    found_control = False
    for scope, retained_root, retained_snapshot in retained:
        source = await store.read_source(scope, retained_root, retained_snapshot)
        found_control |= scope == SCOPE and source.body == RETAINED_BODY
    if not found_control:
        raise AssertionError("retained control source missing")
    unresolved = await rows(
        "SELECT count(*) FROM research_staging.operations o "
        "JOIN research_staging.roots r USING(scope_id,root_id) "
        "LEFT JOIN research_staging.snapshots s ON s.scope_id=o.scope_id AND s.root_id=o.root_id AND s.snapshot_id=o.snapshot_id "
        "WHERE o.state='committed' AND NOT r.deleted AND s.snapshot_id IS NULL"
    )
    if unresolved[0][0] != 0:
        raise AssertionError("live receipt reference unresolved")
    version = await rows("SHOW server_version")
    print(
        json.dumps(
            {
                "schema_version": "fixture-restore-result/1",
                "postgres_version": version[0][0],
                "verified_live_sources": len(retained),
                "deletion_inventory_entries": len(deleted),
                "post_backup_deletion_denied": True,
                "live_receipt_references_resolve": True,
            }
        )
    )


if __name__ == "__main__":
    modes = {
        "restore-seed": seed,
        "restore-delete": delete_and_inventory,
        "restore-verify": verify,
    }
    asyncio.run(modes[sys.argv[1]]())
