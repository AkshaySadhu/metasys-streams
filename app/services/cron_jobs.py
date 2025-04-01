from apscheduler.schedulers.background import BackgroundScheduler
import logging

logger = logging.getLogger(__name__)


def start_cron_job(dump_function, interval_minutes: int = 5):
    """
    Start a cron job to execute dump_function every interval_minutes.
    :param dump_function: Function that dumps events to InfluxDB.
    :param interval_minutes: How often to run the job.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(dump_function, "interval", minutes=interval_minutes)
    scheduler.start()
    logger.info("Cron job started.")
