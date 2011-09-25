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

def send_heartbeat(url, uptime, rwip='0.0.0.0'):
    json_msg = {}
    json_msg['method'] = 'heartbeat'
    json_msg['id'] = 0
    params = {'rwanda-ip':rwip}
    params['kiosk-id'] = Beagleboard.get_dieid()
    if uptime < 60:
        # under a minute
        uptimestr = "%.2f seconds" % uptime
    elif uptime < 60*60:
        # under a hour
        uptimestr = "%.2f minutes" % (uptime/(60.0))
    elif uptime < 60*60*24*3:
        # under 3 days
        uptimestr = "%.2f hours" % (uptime/(60.0*60.0))
    else:
        # over 3 days
        uptimestr = "%.2f days" % (uptime/(60.0*60.0*24.0))
        
    params['uptime'] = uptimestr
    params['sw-version'] = '1.0.0'
    params['time'] = datetime.utcnow()
    json_msg['params'] = params
    jsstr = json.dumps(json_msg)
    hash = MD5.new(jsstr).digest()
    logger.info("System has been up for %s." % uptime)
    
    sign_16encode = Security.sign_digest(hash)
    #print "encoded: %s" % sign_16encode
    #print "signature: %d" % key.sign(hash, "")[0]
    #print "hash: %s"  % "".join(["%02x " % ord(x) for x in hash])
    headers = {'X-eko-signature': sign_16encode}
    
    
    #test decoding
    try:
        logger.info("Transmiting heartbeat.")
        req = urllib2.Request(url, jsstr, headers)
        response = urllib2.urlopen(req)
        the_page = response.read().lower().strip()
    except:
        logger.exception("Transmit failed.")
        return False
    if the_page == "success":
        logger.info("Heartbeat Success.")
        return True
    else:
        logger.info("Sleeping.")
        return False

def main():
    UPTIME = 0
    START = datetime.utcnow()
    
    while True:
        UPTIME = datetime.utcnow() - START
        uptime = UPTIME.seconds
        # check if network is up
        pppdstatus = OSTools.pppd_status()
        if pppdstatus:
            heartbeat_int = 30.0
        else:
            heartbeat_int = 120.0
        if pppdstatus:
            try:
                rwip = OSTools.net_get_ip_address('ppp0')
            except socket.error:
                logger.exception("Error getting local IP")
                rwip = '0.0.0.0'
            try:
                send_heartbeat(Constants.URLJsonAPI, uptime, rwip)
            except:
                logger.exception("Unknown Error")
        time.sleep(heartbeat_int)