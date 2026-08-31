import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler

from agent.config import settings
from agent.graph import run_once

logger = logging.getLogger(__name__)


def run_cycle() -> None:
    try:
        result = run_once()
        logger.info(
            "Cycle complete: %d file(s), %d alert(s) analyzed, %d ticket(s) opened, %d error(s)",
            len(result["files"]),
            len(result["analyzed"]),
            len(result["tickets"]),
            len(result["errors"]),
        )
        for error in result["errors"]:
            logger.warning(error)
    except Exception:  # noqa: BLE001 - one bad cycle must not kill the scheduler
        logger.exception("Unhandled error during triage cycle")


def start() -> None:
    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_cycle,
        "interval",
        minutes=settings.poll_interval_minutes,
        next_run_time=datetime.now(),  # fire once immediately, then every interval
    )
    logger.info("Starting SOC triage agent, polling every %s minute(s)", settings.poll_interval_minutes)
    scheduler.start()
