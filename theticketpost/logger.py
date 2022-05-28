import theticketpost.settings

import os
from time import sleep
from loguru import logger

log_filename = 'theticketpost.log'
log_path = os.path.join(theticketpost.settings.get_storage_path(), log_filename)

logger.add(log_path, format="{time:YYYY-MM-DD HH:mm:ss.SSS} - [{level}] - {message}")

def stream():
    with open(log_path) as log_info:
        while True:
            data = log_info.read()
            yield data.encode()
            sleep(1)

def reset():
    open(log_path, 'w').close()
