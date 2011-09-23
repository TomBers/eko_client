#!/usr/bin/python
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

import os.path

from os import makedirs

from eko.Sensors.Dispatcher import EkoDispatcher

import eko.SystemInterface.OSTools as OSTools

import eko.SystemInterface.Beagleboard as Beagleboard

from eko.ThirdParty import ping

logger = LogHelper.getLoggerInstance()
logger.setLevel(logging.DEBUG)

if __name__=="__main__":
    if not os.path.exists('/data/configdumps'):
        makedirs('/data/configdumps')
    if len(sys.argv) <  2:
        print 'USAGE: configsingle.py [PATH TO CONFIG FILES]'
        sys.exit(0)
    cfgpath = sys.argv[1]
    dispatch = EkoDispatcher(datapath='/data/configdumps', sensorcfgpath=cfgpath)
    dispatch.import_configs()
    logger.info("Dispatching all sensor config operations.")
    dispatch.dispatch_all()