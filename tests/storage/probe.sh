#!/bin/sh
# Only synthetic transport probes. Never an application migration or pilot gate.
set -eu
case "${1:-}" in
  write|read|cleanup) phase=$1 ;;
  *) echo 'Expected write, read, or cleanup' >&2; exit 2 ;;
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
psql -X --set=ON_ERROR_STOP=1 --file="/probes/$phase.sql"
