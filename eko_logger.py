#!/usr/bin/python
"""
The main logger application
"""
# target device may run Python 2.6 so use optparse vs argparse
import optparse
import logging
import sys
import time
import signal

from ConfigParser import ConfigParser

from eko.SystemInterface.DisplayControl import DisplayController

import eko.Util.LogHelper as LogHelper
import eko.Util.DBSetup as DBSetup

import eko.SystemInterface.OSTools as OSTools

import eko.SystemInterface.Beagleboard as Beagleboard

VERSION = '2.0'

def handleSIGTERM():
    sys.exit(0)
    
signal.signal(signal.SIGTERM, handleSIGTERM)
import time

class DataLogger(object):
    datadir = '/data'
    logger = logging.getLogger('eko.DataLogger')
    def __init__(self, cfg):
        config = ConfigParser()
        try:
            config.read(cfg)
        except:
            self.logger.exception("Unable to read config file %s." % cfg)
        
        # try to open the databases
        self.logger.info("Opening databases.")
        try:
            DBSetup.check_databases()
        except:
            self.logger.exception("Databases could not be opened.")
        
        self.disp = DisplayController()
        
    def start(self):
        # open a internet connection
        ## power the modem
        self.disp.control_led('all', False)
        
        try:
            x = Beagleboard.turn_on_usbhub()
        except:
            self.logger.exception("Error encountered when attempting to turn on USB Hub.")
        
        ### raise error led if hub power failed
        if not x:
            self.disp.control_led('neterr', True)
        
        ## wait for system to settle
        time.sleep(30)
        
        ## power off the modem
        try:
            Beagleboard.turn_off_usbhub()
        except:
            self.logger.exception("Error encountered when attempting to power off USB hub.")
        

def main():
    run_count = 0;
    run_error_threshold = 5;
    
    usage = 'usage: %prog [-d] [-v] [-c CONFIG]'
    parser = optparse.OptionParser(usage=usage, version="%prog " + VERSION)
    parser.add_option("-v", "--verbose", help="Print events to stdout.",
                      action="store_true", dest="verbose", default=False)
    parser.add_option("-d", "--debug", help="Enable debug output.",
                      action="store_true", dest="debug", default=False)
    parser.add_option("-c", "--config",
                      dest="configfile", default="/etc/eko/eko.conf",
                      metavar="CONFIG", help="Path to configuration file.")
    
    (options, args) = parser.parse_args()
    if options.configfile:
        configfile = options.configfile
    logger = LogHelper.getLoggerInstance()
    
    # create datalogger instance and run it.
    tx = 1
    while tx == 1:
        tx = 0
        try:
            logger.info("Executing main code with config %s. Attempt #%d." % (configfile, run_count))
            datalogger = DataLogger(configfile)
            time.sleep(5)
            datalogger.start()
        except KeyboardInterrupt:
            sys.exit(1)
        except:
            run_count += 1;
            if run_count > run_error_threshold:
                logger.critical("Too many crashes, exiting.")
                sys.exit(-1)
            logger.exception("DataLogger crashed! Attempting to retry.")
if __name__=="__main__":
    main()