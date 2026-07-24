"""Detection round: fetch CWA data, diff against state, notify, persist.

Replaces ``AlertService``. One ``run_once`` call is one round — the daemon's
JobQueue invokes it every POLL_INTERVAL_SECONDS, and ``--once`` runs a single
round for cron/Lambda setups. All rounds share an asyncio lock with the mute
commands so state writes never interleave.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union
from zoneinfo import ZoneInfo

from loguru import logger

from domain.alert_checker import is_alert_valid
from infrastructure import cwb_client, healthcheck, radar, state_repo
from infrastructure.message_format import alert_buttons, format_all_clear, format_digest
from infrastructure.telegram import TelegramSender

TW = ZoneInfo("Asia/Taipei")


@dataclass
class CheckResult:
    time: datetime
    ok: bool
    new_count: int
    error: Optional[str] = None
    consecutive_failures: int = 0  # unbroken run of failed rounds after this one


class Monitor:
    def __init__(
        self,
        config: dict[str, Any],
        sender: TelegramSender,
        lock: asyncio.Lock,
        state_path: Union[str, Path] = "state.json",
        radar_path: str = "crop.jpg",
    ):
        self.areas = config["AREAS"]
        self.token = config["CWB_TOKEN"]
        self.healthcheck_url = config.get("HEALTHCHECK_URL", "")
        # Only ping /fail after this many consecutive failed rounds, so a single
        # transient CWA blip does not page. The dead-man's-switch grace period on
        # healthchecks.io covers the sub-threshold gap.
        self.fail_threshold = max(1, int(config.get("HEALTHCHECK_FAIL_THRESHOLD", 3) or 3))
        self.sender = sender
        self.lock = lock
        self.state_path = state_path
        self.radar_path = radar_path

    async def run_once(self) -> CheckResult:
        async with self.lock:
            result = await self._run(datetime.now(TW))
        # Ping outside the lock: best-effort network I/O must not block the mute
        # commands that share it. A successful round pings the base URL (the
        # dead-man's-switch heartbeat); a failed round pings /fail only once it
        # has failed self.fail_threshold times in a row. A sub-threshold failure
        # pings nothing and leaves the heartbeat to lapse into the grace period,
        # so one transient CWA blip never pages.
        if result.ok:
            await healthcheck.ping(self.healthcheck_url, fail=False)
        elif result.consecutive_failures >= self.fail_threshold:
            await healthcheck.ping(self.healthcheck_url, fail=True)
        return result

    async def _run(self, now: datetime) -> CheckResult:
        state = state_repo.load_state(self.state_path)
        try:
            doc = await asyncio.to_thread(cwb_client.get_thunder_data, self.token)
            current = is_alert_valid(doc, self.areas)
        except Exception as e:
            logger.exception("Thunder data fetch failed")
            state.consecutive_failures += 1
            result = CheckResult(
                now, False, 0, str(e), consecutive_failures=state.consecutive_failures
            )
            self._finish(state, result)
            return result

        new_alerts = [a for a in current if a not in state.active_alerts]
        if new_alerts:
            if state.episode_started is None:
                state.episode_started = min(a.occur_time for a in new_alerts)
            state.episode_count += len(new_alerts)
            state.history.extend(new_alerts)
            state.prune_history(now)
            await self._notify_alerts(state, new_alerts, now)
        elif not current and state.active_alerts:
            await self._notify_all_clear(state, now)
            state.episode_started = None
            state.episode_count = 0

        state.active_alerts = current
        state.consecutive_failures = 0  # a good round breaks any failure streak
        result = CheckResult(now, True, len(new_alerts))
        self._finish(state, result)
        return result

    async def _notify_alerts(self, state: state_repo.State, new_alerts: list, now: datetime) -> None:
        if state.is_muted(now):
            logger.info("Muted: skipped digest for {} new strikes", len(new_alerts))
            return
        text = format_digest(new_alerts, self.areas, now)
        latest = max(new_alerts, key=lambda a: a.occur_time)
        img_path = None
        try:
            img_path = await asyncio.to_thread(radar.download_radar, self.radar_path)
        except Exception as e:
            logger.warning(f"Radar image failed, alert goes text-only: {e}")
        delivered = await self.sender.send_alert(text, img_path=img_path, buttons=alert_buttons(latest))
        logger.info("Digest delivery ({} new) -> {}", len(new_alerts), delivered)

    async def _notify_all_clear(self, state: state_repo.State, now: datetime) -> None:
        if state.is_muted(now):
            logger.info("Muted: skipped all-clear")
            return
        delivered = await self.sender.send_text(
            format_all_clear(state.episode_started, state.episode_count, now)
        )
        logger.info("All-clear delivery -> {}", delivered)

    def _finish(self, state: state_repo.State, result: CheckResult) -> None:
        state.last_check = state_repo.LastCheck(
            time=result.time.isoformat(),
            ok=result.ok,
            new_count=result.new_count,
            error=result.error,
        )
        state_repo.save_state(state, self.state_path)
