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

from eko_logger import DataLogger

logger = LogHelper.getLoggerInstance()
logger.setLevel(logging.DEBUG)

datalogger=DataLogger('/etc/eko/eko.cfg')
datalogger.netsync()
