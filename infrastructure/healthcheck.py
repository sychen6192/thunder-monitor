"""Best-effort healthchecks.io dead-man's-switch ping.

The daemon pings after every detection round: the base URL on success, the
``/fail`` endpoint on a failed round. A missing ping — process dead, machine
down, or rounds silently failing (e.g. a fetch that never succeeds) — trips
healthchecks.io's alert after its configured grace period, catching the
"container is Up but doing nothing" failure that Docker's restart policy
cannot see. Pinging is best-effort: every error is swallowed and logged so it
can never break a detection round. An empty URL disables it.
"""

import logging

import httpx

logger = logging.getLogger(__name__)


async def ping(base_url: str, *, fail: bool = False) -> None:
    if not base_url:
        return
    url = base_url.rstrip("/")
    if fail:
        url += "/fail"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.get(url)
    except Exception as e:  # network error, timeout, bad URL — never break the round
        logger.warning("Healthcheck ping failed: %s", e)
