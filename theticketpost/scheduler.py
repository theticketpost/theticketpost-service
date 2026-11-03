import theticketpost.newspaper

from threading import Thread
from loguru import logger
import time
import schedule

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DEFAULT_PORT = 8080


class Scheduler(Thread):
    def __init__(self, config):
        Thread.__init__(self, daemon=True)
        logger.info("Starting scheduler...")
        self.config = config
        self.set_schedule(config)
        logger.info("Scheduler started")

    def run(self):
        while True:
            schedule.run_pending()
            time.sleep(1)

    def print_newspaper(self):
        logger.info("Initializing scheduler callback")
        device = self.config.get("printer", {}).get("device")
        if device:
            port = self.config.get("webserver", {}).get("port", DEFAULT_PORT)
            theticketpost.newspaper.print(device["address"], port)
        else:
            logger.error("Printer not configured")


    def set_schedule(self, config):
        self.config = config
        schedule.clear()
        days = config.get("schedule", {})
        for day in DAYS:
            entry = days.get(day) or {}
            if not entry.get("active"):
                continue
            try:
                getattr(schedule.every(), day).at(entry.get("time", "")).do(self.print_newspaper)
                logger.info(f"Newspaper scheduled on {day} at {entry['time']}")
            except schedule.ScheduleValueError as e:
                logger.error(f"Invalid time for {day}: {e}")
