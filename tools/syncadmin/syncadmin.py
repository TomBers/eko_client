#!/usr/bin/python
import logging
import sys
import time

from ConfigParser import ConfigParser

import eko.Util.LogHelper as LogHelper
import eko.Util.DBSetup as DBSetup
import eko.WebService.Uploader as Uploader
import os.path

from os import makedirs

from eko.Sensors.Dispatcher import EkoDispatcher

import eko.SystemInterface.OSTools as OSTools

import eko.SystemInterface.Beagleboard as Beagleboard




if __name__=="__main__":
    logger = LogHelper.getLoggerInstance()
    uploader = Uploader.DataUploader()
    print("%d Files Left to Sync\n" % uploader.get_filelist())
    print('-'*20+'\n')
    print('Id\tName\n')
    for file in uploader.filelist:
        print "%s\t%s" % (str(file[0]), str(file[1]))
    