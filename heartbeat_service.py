#!/usr/bin/python

### HEARTBEAT SERVICE

import logging
import eko.WebService.Heartbeat as Heartbeat
from logging.handlers import RotatingFileHandler
logger = logging.getLogger('eko')

if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    formatter_c = logging.Formatter('[%(levelname)s] - %(asctime)s - %(name)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)
    ch.setFormatter(formatter_c)
    logger.addHandler(ch)
    formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(name)s - %(module)s(%(lineno)d) %(funcName)s - %(message)s')    
    fh = RotatingFileHandler('/home/root/eko.heartbeat.log', maxBytes=20000, backupCount=5)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    Heartbeat.main()