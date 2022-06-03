import theticketpost.newspaper

from threading import Thread
from loguru import logger
import time
import schedule

class Scheduler(Thread):
    def __init__(self, config):
        Thread.__init__(self)
        logger.info("Starting scheduler...")
        self.set_schedule(config)
        self.config = config
        logger.info("Scheduler started")

    def run(self):
        while True:
            schedule.run_pending()
            time.sleep(1)

    def print_newspaper(self):
        logger.info("Initializing scheduler callback")
        if ("printer" in self.config and self.config["printer"]["device"]):
            port = self.config["webserver"]["port"]
            address = self.config["printer"]["device"]["address"]
            theticketpost.newspaper.print(address, port)
        else:
            logger.error("Printer not configured")


    def set_schedule(self, config):
        self.config = config
        schedule.clear()
        if ( "schedule" in config ):
            if config["schedule"]["monday"]["active"]:
                schedule.every().monday.at(config["schedule"]["monday"]["time"]).do(self.print_newspaper)
            if config["schedule"]["tuesday"]["active"]:
                schedule.every().tuesday.at(config["schedule"]["tuesday"]["time"]).do(self.print_newspaper)
            if config["schedule"]["wednesday"]["active"]:
                schedule.every().wednesday.at(config["schedule"]["wednesday"]["time"]).do(self.print_newspaper)
            if config["schedule"]["thursday"]["active"]:
                schedule.every().thursday.at(config["schedule"]["thursday"]["time"]).do(self.print_newspaper)
            if config["schedule"]["friday"]["active"]:
                schedule.every().friday.at(config["schedule"]["friday"]["time"]).do(self.print_newspaper)
            if config["schedule"]["saturday"]["active"]:
                schedule.every().saturday.at(config["schedule"]["saturday"]["time"]).do(self.print_newspaper)
        return
