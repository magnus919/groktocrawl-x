# Experimental replacement candidate

This runbook deploys the `groktocrawl-x` replacement candidate as an isolated
experiment. It does not replace the mainline GroktoCrawl project or switch the
existing production deployment. The candidate has its own Compose project,
containers, images, networks, volumes, database, and loopback-only ports.

The first candidate uses PostgreSQL as the authority for retained research
artifacts and pgvector for semantic serving. Qdrant remains in the candidate as
an unchanged rollback target until the migration and rollback rehearsal in W9
is complete. The incumbent deployment is not a rollback target and is never
mutated by this procedure.

## Frozen topology

| Responsibility | Candidate service | Durable state |
|---|---|---|
| Job and execution coordination | `candidate-valkey` | `candidate_valkey_data` |
| Research artifact authority | `candidate-postgres` | `candidate_postgres_data` |
| Semantic serving | `candidate-semantic` using pgvector | PostgreSQL projection |
| Semantic rollback | `candidate-qdrant-rollback` | `candidate_qdrant_rollback_data` |
| Web discovery | `candidate-slopsearx` | Valkey cache only |
| Acquisition | `candidate-scraper` and `candidate-browser` | candidate browser cache |
| HTTP research API | `candidate-agent` | PostgreSQL and Valkey above |
| Portal health dependency | `candidate-portal` | no independent durable authority |
| MCP transport | `candidate-mcp` | no independent durable authority |

Only the HTTP API and MCP transport publish ports, both on `127.0.0.1` by
default. The project name is fixed as `groktocrawl-x-candidate`; every service
and volume also carries a candidate-specific name. Do not combine this file with
`docker-compose.yml`.

## Prepare a clean target

Check out the exact reviewed revision on the target host. Then create private
credentials outside the repository:

```sh
umask 077
openssl rand -hex 32 > /tmp/groktocrawl-x-postgres-password
openssl rand -hex 32 > /tmp/groktocrawl-x-api-key
cp .env.experimental-candidate.sample /tmp/groktocrawl-x-candidate.env
chmod 600 /tmp/groktocrawl-x-postgres-password \
  /tmp/groktocrawl-x-api-key \
  /tmp/groktocrawl-x-candidate.env
```

Edit `/tmp/groktocrawl-x-candidate.env`:

- set `CANDIDATE_IMAGE_TAG` to the full checked-out Git revision;
- set the PostgreSQL password-file path to the file just created;
- set `CANDIDATE_API_KEY` to the value in the API-key file;
- set the LiteLLM URL and private key for `gpuslut01`;
- set the SlopSearX search-provider key.

The checked-in sample selects LiteLLM's `local` model alias. Keep secrets in
the private environment and credential files; never add them to a receipt or
commit them.

On a genuinely clean target, this command must return no candidate resources:

```sh
docker ps -a --filter label=com.docker.compose.project=groktocrawl-x-candidate
docker volume ls --filter label=com.docker.compose.project=groktocrawl-x-candidate
```

If it lists resources, preserve them and investigate their owner. Do not delete
volumes merely to make the clean-start check pass.

## Resolve, build, and start

Use the same file and private environment for every command:

```sh
export CANDIDATE_ENV=/tmp/groktocrawl-x-candidate.env
export CANDIDATE_COMPOSE=compose.experimental-candidate.yml

docker compose --env-file "$CANDIDATE_ENV" -f "$CANDIDATE_COMPOSE" config --quiet
docker compose --env-file "$CANDIDATE_ENV" -f "$CANDIDATE_COMPOSE" config --services
docker compose --env-file "$CANDIDATE_ENV" -f "$CANDIDATE_COMPOSE" build --pull
docker compose --env-file "$CANDIDATE_ENV" -f "$CANDIDATE_COMPOSE" up -d --wait
```

There are no fixed sleeps. Compose waits for the declared health checks. On the
first start, PostgreSQL applies the ordered research migrations through schema
14, and the semantic service creates the pgvector projection before becoming
ready. The semantic health response must identify pgvector as the serving store
and Qdrant as rollback-ready.

## Verify and freeze the receipt

Load only the candidate API key into the verifier process and write the receipt
outside the repository first:

```sh
export CANDIDATE_API_KEY=$(sed -n 's/^CANDIDATE_API_KEY=//p' "$CANDIDATE_ENV")
UV_CACHE_DIR=/tmp/groktocrawl-x-uv-cache uv run \
  scripts/verify_experimental_candidate.py \
  --env-file "$CANDIDATE_ENV" \
  --compose-file "$CANDIDATE_COMPOSE" \
  --output /tmp/groktocrawl-x-candidate-receipt.json
```

The verifier fails unless all of these complete:

- aggregate service health;
- PostgreSQL research schema 14 and the pgvector extension;
- the experimental capability document identifying PostgreSQL artifact authority;
- one admitted research run, completed artifact set, and terminal SSE replay;
- retrieval of the manifest plus summary, analysis, and dossier bytes;
- one real SlopSearX search through HTTP and through the repository CLI;
- MCP initialization and the `research_capabilities` tool;
- capture of the source revision, lockfile and Compose hashes, resolved container
  image identities, and running service state.

The JSON receipt deliberately excludes environment values, credentials, private
addresses, and artifact bodies. Review it before copying it into the W9 evidence
packet.

## Stop without destroying evidence

```sh
docker compose --env-file "$CANDIDATE_ENV" -f "$CANDIDATE_COMPOSE" stop
```

Use `start` followed by the verifier for the restart check. `down` removes
containers and networks while preserving named volumes. Do not use `down -v`;
volume removal belongs only to the later, separately reviewed retirement step.

## Failure boundary

If candidate readiness or verification fails, stop admitting experimental work,
capture `docker compose ps` and service logs, and leave the incumbent deployment
unchanged. During the pgvector rehearsal, switching the candidate semantic mode
back to Qdrant is the rollback operation. Deleting PostgreSQL or Qdrant data is
never part of rollback.
