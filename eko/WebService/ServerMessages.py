import eko.SystemInterface.Beagleboard as Beagleboard

from datetime import datetime

import Crypto.Hash.MD5 as MD5

import eko.ThirdParty.simplejson_with_datetime as json
import urllib2

from eko.ThirdParty.baseconv import BaseConverter

import eko.Util.Security as Security

import logging

import time

import eko.SystemInterface.OSTools as OSTools
import socket

import eko.Constants as Constants

logger = logging.getLogger('eko.webservice.servermessages')

# gets server messages:

class ServerMessage(object):
    def __init__(self):
        