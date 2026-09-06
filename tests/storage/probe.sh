#!/bin/sh
# Only synthetic transport probes. Never an application migration or pilot gate.
set -eu
case "${1:-}" in
  write|read|cleanup|adapter|revision|publication|rerender|export|import|expiry|research-import|research-publication-state|research-export|research-publication|research|research-state|import-state|publication-state|revision-state|source-state|restore-seed|restore-delete|restore-verify) phase=$1 ;;
  *) echo 'Expected a documented storage test phase' >&2; exit 2 ;;
esac
umask 077
PGPASSFILE=$(mktemp /tmp/research-pgpass.XXXXXX)
export PGPASSFILE
trap 'rm -f "$PGPASSFILE"' EXIT HUP INT TERM
# Require hex-only generated credentials so pgpass separators need no escaping.
password=$(cat /run/secrets/research_password)
case "$password" in
  ''|*[!0-9a-fA-F]*) echo 'Use a hex password file (openssl rand -hex 32)' >&2; exit 2 ;;
esac
printf '%s:%s:%s:%s:%s\n' "$PGHOST" 5432 "$PGDATABASE" "$PGUSER" "$password" > "$PGPASSFILE"
unset password
case "$phase" in
research-import) python /probes/test_research_import_db.py; exit ;;
research-export) python /probes/test_research_bundle_db.py; exit ;;
research-publication) python /probes/test_research_publication_db.py; exit ;;
research) python /probes/test_research_store_db.py; exit ;;
expiry) python /probes/test_expiry_store_db.py; exit ;;
import) python /probes/test_import_store_db.py; exit ;;
export) python /probes/test_artifact_bundle_db.py; exit ;;
rerender) python /probes/test_rerender_store_db.py; exit ;;
publication) python /probes/test_publication_store_db.py; exit ;;
revision) python /probes/test_revision_store_db.py; exit ;;
source-state|revision-state|publication-state|import-state|research-state|research-publication-state) python /probes/restore_source_store.py "$phase"; exit ;;
restore-*) python /probes/restore_source_store.py "$phase"; exit ;;
esac
if [ "$phase" = adapter ]; then
  python /probes/test_source_store_db.py
else
  psql -X --set=ON_ERROR_STOP=1 --file="/probes/$phase.sql"
fi
