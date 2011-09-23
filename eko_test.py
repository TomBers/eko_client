import optparse
import logging
import sys
import time
import signal
import socket
import urllib2

from ConfigParser import ConfigParser

from eko.SystemInterface.DisplayControl import DisplayController

import eko.Util.LogHelper as LogHelper
import eko.Util.DBSetup as DBSetup

from eko.Sensors.Dispatcher import EkoDispatcher

import eko.SystemInterface.OSTools as OSTools

import eko.SystemInterface.Beagleboard as Beagleboard

from eko.ThirdParty import ping

logger = LogHelper.getLoggerInstance()
logger.setLevel(logging.DEBUG)

dispatch = EkoDispatcher()
dispatch.import_configs()
logger.info("Dispatching all sensor polling operations.")
dispatch.dispatch_all()