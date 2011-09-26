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

logger = logging.getLogger('eko.webservice.clientmessages')

def _update_clientmsg_table(ids, configpath=Constants.CONFIGPATH):
    con = sqlite3.connect(join(configpath, 'sync.db'))
    logger.debug("Updating records with ids: %s" % ("".join(["%s " % i for i in ids])))
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

def add_clientmessage(message, sessionref, origin, origintime):
    con = sqlite3.connect(join(Constants.CONFIGPATH, 'sync.db'))
    c = con.cursor()
    try:
        c.execute("INSERT INTO clientmsg (message, sessionref, origin, origintime) VALUES (?, ?, ?, ?)",
                (message,sessionref, origin, origintime))
    except sqlite3.Error:
        logger.exception("Error inserting message: %s to db." % message)
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
        c.execute("SELECT message, sessionref, origin, origintime, id FROM clientmsg WHERE synctime is NULL LIMIT 15")
        rows = c.fetchall()
    except sqlite3.Error:
        logger.exception("Error fetching rows from sync.db.")
        rows = None
    finally:
        c.close()
        con.close()
    
    # bug out if execute failed
    if (rows is None) or (rows == []):
        logger.info("No messages to sync.")
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
    try:
        resp_str = resp.read()
        jsonreply = json.loads(resp_str)
        logger.debug("JSON reply reads: %s" % resp_str)
    except:
        logger.exception("Could not read reply json.")
        jsonreply = {'result':'Could not load json'}
    
    if jsonreply['result'].lower().strip() != 'success':
        logger.error("Server replied with error: %s" % str(jsonreply))
        return False
    else:
        logger.info("Succesfully uploaded messages.")
        _update_clientmsg_table([row[4] for row in rows])
        return True