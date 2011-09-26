import optparse
import logging
import sys
import time
import signal
import socket
import urllib2

from datetime import datetime

from ConfigParser import ConfigParser

from eko.SystemInterface.DisplayControl import DisplayController

import eko.Util.LogHelper as LogHelper
import eko.Util.DBSetup as DBSetup

from eko.Sensors.Dispatcher import EkoDispatcher

import eko.SystemInterface.OSTools as OSTools

import eko.SystemInterface.Beagleboard as Beagleboard

from eko.ThirdParty import ping
import eko.WebService.ClientMessages as CMsgs

from eko_logger_alwayson_net import DataLogger

logger = LogHelper.getLoggerInstance(verbose_level=logging.DEBUG)
logger.setLevel(logging.DEBUG)

def upload_data():
    datalogger=DataLogger('/etc/eko/eko.cfg')
    datalogger.upload_data_messages()
    datalogger.upload_kiosk_messages()
    datalogger.download_server_messages()
    datalogger.upload_logs()

def insert_kiosk_messages():
    CMsgs.add_clientmessage('ABCDEF\nLoremIpsum', '1234', 'Test', datetime.utcnow())
    CMsgs.add_clientmessage('Gazzzz\nLoremIpsum', '2', 'Test', datetime.utcnow())
    CMsgs.add_clientmessage('ABCDEF\Booo', '3', 'cxcx', datetime.utcnow())
    CMsgs.add_clientmessage('Lolololol\nLoremIpsum', '5', '3', datetime.utcnow())
    return

if __name__ == "__main__":
    insert_kiosk_messages()
    upload_data()

    