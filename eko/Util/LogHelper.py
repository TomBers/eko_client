import logging
from logging.handlers import TimedRotatingFileHandler



def getLoggerInstance(level=logging.DEBUG, addhandler=True, verbose_level=logging.DEBUG):
    logger = logging.getLogger('eko')
    logger.setLevel(logging.DEBUG)
    formatter_c = logging.Formatter('[%(levelname)s] - %(asctime)s - %(name)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setLevel(verbose_level)
    ch.setFormatter(formatter_c)
    logger.addHandler(ch)
    formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(name)s - %(module)s(%(lineno)d) %(funcName)s - %(message)s')    
    fh = TimedRotatingFileHandler('/var/log/eko', when='midnight', backupCount=10)
    fh.setLevel(level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger