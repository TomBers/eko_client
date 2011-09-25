#!/usr/bin/python

### HEARTBEAT SERVICE

import logging
import eko.WebService.Heartbeat as Heartbeat

logger = logging.getLogger('eko')

if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    formatter_c = logging.Formatter('[%(levelname)s] - %(asctime)s - %(name)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter_c)
    logger.addHandler(ch)
    Heartbeat.main()