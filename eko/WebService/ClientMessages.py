import eko.ThirdParty.simplejson_with_datetime as json
import urllib2
import sqlite3

from os.path import join

from datetime import datetime

from Crypto.Hash import MD5
import Crypto.PublicKey.RSA as RSA

import eko.Constants as Constants

import eko.SystemInterface.Beagleboard as Beagleboard

import eko.Util.Security as Security

import logging

logger = logging.getLogger('eko.webservice.clientmsg')

def _update_clientmsg_table(ids, configpath=Constants.CONFIGPATH):
    con = sqlite3.connect(join(configpath, 'sync.db'))
    c = con.cursor()
    for id in ids:
        try:
            c.execute("UPDATE clientmsg SET synctime = ? WHERE id = ?", (datetime.utcnow(), id))
        except sqlite3.Error:
            logger.exception("Error updating client messages table.")
    con.commit()
    c.close()
    con.close()
    return

def transmit_clientmessages(configpath=Constants.CONFIGPATH):
    # upload
    logger.info("Transmitting client messages to server.")
    con = sqlite3.connect(join(configpath, 'sync.db'))
    c = con.cursor()
    try:
        c.execute("SELECT message, sessionref, origin, origintime FROM clientmsg WHERE synctime is NULL LIMIT 15")
        rows = c.fetchall()
    except sqlite3.Error:
        logger.exception("Error fetching rows from sync.db.")
        rows = None
    finally:
        c.close()
        con.close()
    
    # bug out if execute failed
    if rows is None:
        return False
    
    list = []
    for row in rows:
        data={}
        data['session-ref'] = row[1]
        data['message'] = row[0]
        data['origin'] = row[2]
        data['origin-date'] = row[3]
        list.append(data)
    
    # list contains a list of messages
    msg = {}
    msg['method'] = 'post_messages'
    msg['id'] = 0
    msg['params'] = {'kiosk-id' : Beagleboard.get_dieid(), 'messages' : list}
    
    jsonstr = json.dumps(msg)
    
    hash = MD5.new(jsonstr).digest()
    
    sig = Security.sign_digest(hash)
    headers = {'X-eko-signature':  sig}
    urlreq = urllib2.Request(Constants.URLJsonAPI, jsonstr, headers)
    
    try:
        resp = urllib2.urlopen(urlreq)
    except urllib2.URLError:
        logger.exception("Unable to send client messages")
        return False
    
    jsonreply = json.loads(resp.read())
    if jsonreply['error'] != None:
        logger.error("Server replied with error: %s" % str(jsonreply))
        return False
    else:
        _update_clientmsg_table([row[0] for row in rows])
        return True