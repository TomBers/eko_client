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

def get_messages():
    json_query = {}
    json_query['method'] = 'get_messages'
    json_query['id'] = '0'
    json_query['params'] = {'kiosk-id': Beagleboard.get_dieid()}
    json_query_str = json.dumps(json_query)
    logger.debug("Sending JSON Query: %s" % json_query_str)
    hash = MD5.new(json_query_str).digest()
    # encoding signature
    encoded_sig = Security.sign_digest(hash)
    headers = {'X-eko-signature': encoded_sig}
    
    urlreq = urllib2.Request(Constants.URLJsonAPI, json_query_str, headers)
    try:
        response = urllib2.urlopen(urlreq)
    except urllib2.URLError:
        logger.exception("Unable to open URL to fetch server messages")
        return False
    
    json_reply = response.read()
    
    try:
        response_dict = json.loads(json_reply)
    except:
        logger.exception("Unable to decode response JSON!")
        return False
    
    messages = response_dict['result']
    return messages
