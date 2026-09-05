# Experimental runtime CI

This runbook applies only to `magnus919/groktocrawl-x`. The experimental fork is
not a replacement for mainline. Tracking: issue #7, experiment W0.

## Validation and publication are separate

[Runtime CI](../../.github/workflows/runtime.yml) runs on PRs and pushes to `main`.
It has read-only repository permissions, no provider/registry credentials and no
self-hosted jobs. GitHub-hosted runners build application and fixture images from
the checked-out source. A [CI Compose override](../../docker-compose.ci.yml) gives
those images local names, replaces the live search service with the deterministic
search fixture, and makes the model cache volume private to the Compose project.
Production Compose settings are unchanged.

The inherited [Docker Build & Publish](../../.github/workflows/docker.yml) stays
disabled, including its old integration job. It remains historical reference for
existing workflow contracts; its hardcoded upstream publishing targets must never
be enabled unchanged. The new workflow neither calls it nor waits for publication.
A later release change must define fork-owned names, credentials and release rules.

Runtime Gate requires successful change classification and every selected test job.
Missing outputs, failed classification, cancellation and skipped required jobs fail
closed. Documentation-only changes explicitly report that Docker tests were not
required. Runtime changes run the inherited critical journey, integration/service
suite and coverage gates; hosted twin selection follows the shared classifier.
The inherited exclusions remain visible in the workflow (external/observability
cases and contracts run separately on the host). Fixture success does not prove
live-provider quality or production capacity.

## First-run verification and limits

The first PR run must establish that the hosted runner can build and execute the
full stack. Integration has a 60-minute job ceiling and two concurrent Compose
build operations. Public package, base-image and model downloads still need network
access; the Docker lane is not claimed to be fully network-isolated. Search and LLM
traffic uses fixtures and no paid-provider secrets are supplied. The separate
hosted twin job enforces its existing loopback-only test restrictions.

Inspect build/startup failures, runner disk/RAM, model readiness, test outcomes and
coverage before accepting the lane as operational. Downloaded model capacity and
cold-start time may exceed the hosted runner's bounds; that is a failing CI setup
to resolve, not a reason to mark Runtime Gate successful or silently omit services.
Sanitized fixture diagnostics, twin provenance, test outcomes, coverage and failure
logs are uploaded; teardown removes only this job's Compose resources and volumes.

Once merged, verify workflow enablement and a docs-only and runtime-changing run.
Check actual repository rulesets separately: declaring a job named Runtime Gate
does not make it required. W0 remains incomplete until required checks and review
policy are configured and verified. Keep publishing, paid review, live calibration
and inherited self-hosted execution disabled.
