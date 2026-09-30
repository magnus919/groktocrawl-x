# Browser and scraper memory study v1

Preregistered before measurement for #392. No runtime or configuration changes.

Run six serial blocks, each containing ten browser create / fixed synthetic DOM / getContent / delete cycles and ten equivalent public-document scrapes. Use the same URL throughout. Do not clear caches, navigate to private URLs, or destroy other users' sessions. Pause fifteen seconds after each block; then take six idle samples thirty seconds apart. Maximum workload: sixty browser cycles and sixty scrapes. No model calls.

Measure cgroup usage, anonymous memory, file cache, summed process RSS, active browser sessions, health, OOM counters, and restart/container continuity. RSS can double-count shared pages; interpret alongside anonymous cgroup memory. Record each workload step and settled/idle samples. Persist only normalized values and counts, never credentials, endpoint URLs, Docker identifiers or raw responses.

Stop at 80% of either finite effective memory limit, a new OOM event, restart, unhealthy service, changed runtime metadata, or any failed operation. API operations have sixty-second limits; infrastructure commands have thirty-second limits. Always delete a created session after execution, even on failure. TTL provides a backup expiry if deletion itself fails.

Compare block-settled anonymous memory and total usage; a late-block spread at most 32 MiB supports short-term stabilization. A monotonic increase exceeding 64 MiB over settled blocks warrants investigation. Intermediate patterns are inconclusive. Compare final idle memory with baseline; useful retained cache is not automatically a leak. These are engineering thresholds, not significance tests, and six sequential blocks are not independent experimental subjects.

Browser synthetic DOM lifecycle and scraper document capture are distinct workload strata. The scraper may use content negotiation or cache and therefore this study cannot qualify all Playwright scraper paths. Other users' work can confound results; unexpected active sessions or unexplained growth must be disclosed. A short study cannot rule out a long-running leak. Retain/revise conclusions must remain bounded accordingly.

Command: `python scripts/measure_memory_soak.py --env-file ENV --compose-file BASE --compose-file OVERRIDE --base-url API --scrape-url PUBLIC_DOCUMENT --output PRIVATE_RECEIPT`. Run on the deployment host. Review and sanitize the receipt before committing it. No deployment-specific command values belong in the repository.
