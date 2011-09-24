"""
This module contains function which verify the integrity of the sqlite database. If
necessary the script can recreate the database.
"""

import os
import sqlite3
import logging

from datetime import datetime
from os.path import join, splitext, exists, isdir, relpath, isfile
import tempfile
import shutil


CFG_ROOT = "/etc/eko"

logger = logging.getLogger('eko.dbsetup')

CREATE_FILELIST_TBL = """
CREATE TABLE IF NOT EXISTS filelist (id INTEGER PRIMARY KEY, filename VARCHAR, 
        synctime DATETIME)
"""


CREATE_SERVER_MSG_TBL = """
CREATE TABLE IF NOT EXISTS servermsg (id INTEGER PRIMARY KEY, msg VARCHAR, 
        msgtype VARCHAR, senttime DATETIME, synctime DATETIME, showtime DATETIME)
"""

CREATE_CLIENT_MSG_TBL = """
CREATE TABLE IF NOT EXISTS clientmsg (id INTEGER PRIMARY KEY, message VARCHAR, 
        sessionref VARCHAR, origin VARCHAR, origintime DATETIME, synctime DATETIME)
"""

CREATE_SERVER_CMD_TBL = """
CREATE TABLE IF NOT EXISTS servercmd (id INTEGER PRIMARY KEY, command VARCHAR, 
        time DATETIME, executed DATETIME, reported DATETIME)
"""

CREATE_SYNCLOG_TBL = """
CREATE TABLE IF NOT EXISTS synclog (id INTEGER PRIMARY KEY, time DATETIME,
        payload VARCHAR, size INTEGER, checksum VARCHAR, files TEXT)
"""

SYNC_DB_NAME = "sync.db"

def check_databases():
    """Performs a filesystem check on the databases before checking them for integrity"""
    logger.info("Checking database sanity.")
    logger.info("Configuration root is %s." % CFG_ROOT)
    try:
        if not _check_db_file('filelist.db'):
            logger.error('filelist.db check failed!')
            try:
                logger.warning('creating new filelist.db')
                _create_filelist_db(newfile=True)
            except (sqlite3.Error, IOError):
                logger.exception('failed to create new filelist.db')
                logger.critical('Database initialisation failure!')
    except:
        logger.exception('filelist.db check failed!')
        logger.critical('filesystem failure')
    finally:
        _create_filelist_db(newfile=False)
    # sync.db
    try:
        if not _check_db_file('sync.db'):
            logger.error('sync.db check failed!')
            try:
                logger.warning('creating new sync.db')
                _create_sync_db(newfile=True)
            except (sqlite3.Error, IOError):
                logger.exception('failed to create new sync.db')
                logger.critical('Database initialisation failure!')
    except:
        logger.exception('sync.db check failed!')
        logger.critical('filesystem failure')
    finally:
        _create_sync_db(newfile=False)
    return
    
def _check_db_file(filename):
    if isfile(join(CFG_ROOT, filename)):
        logger.debug("Database %s exists" % filename)
    else:
        logger.error("Database %s does not exist." % filename)
        return False
        
    fsize = os.stat(join(CFG_ROOT, filename)).st_size
    if fsize:
        logger.info("Database %s is %d bytes." % (filename, fsize))
    else:
        logger.error("Unable to stat database %s size." % filename) 
        return False
        
    try:
        conn = sqlite3.connect(join(CFG_ROOT, filename))
    except:
        logger.exception("Unable to connect to database file %s." % filename)
        return False
        
    try:
        l = conn.execute("pragma table_info(sqlite_master)").fetchall()
        if len(l) == 0:
            logger.error("Database table_info is empty: %s." % filename)
            return False
    except:
        logger.exception("Unable to read database file %s." % filename)
        conn.close()
        return False
    finally:
        conn.close()
        
    try:
        conn = sqlite3.connect(join(CFG_ROOT, filename), timeout=500.0)
        l = conn.execute("VACUUM")
        logger.info("Ran VACUUM on %s" % filename)
        conn.commit()
    except:
        logger.exception("Vaccum of db failed")
        conn.close()
        return False
    finally:
        conn.close()
    return True



def _create_sync_db(newfile=True):
    if newfile or not isfile(join(CFG_ROOT, 'sync.db')):
        if isfile(join(CFG_ROOT,'sync.db')):
            #backup the old file if it is present
            bkname = 'sync.db.%s' % datetime.now().strftime("%d%b%y.%H%M%S")
            try:
                shutil.move(join(CFG_ROOT, 'sync.db'), join(CFG_ROOT, bkname))
                logger.info("Backing up old (corrupted?) sync.db to %s" % bkname)
            except:
                logger.exception("Unable to backup sync.db")
        if isfile(join(CFG_ROOT, 'sync.db')):
            logger.warning("sync.db still present (???).")
            try:
                os.remove(join(CFG_ROOT, 'sync.db'))
            except:
                logger.exception("Unable to delete sync.db.")
                logger.critical("Filesystem Error")
    # try to create a sqlite instance
    try:
        conn = sqlite3.connect(join(CFG_ROOT, 'sync.db'))
        logger.debug("Connection open to sync.db.")
        conn.execute(CREATE_CLIENT_MSG_TBL)
        conn.execute(CREATE_SERVER_CMD_TBL)
        conn.execute(CREATE_SERVER_MSG_TBL)
        conn.execute(CREATE_SYNCLOG_TBL)
        logger.debug("CREATE statement executed on sync.db")
        conn.commit()
        logger.info("sync.db ready")
    except:
        logger.exception("Cannot connect to sync.db")
    finally:
        conn.close()
        
def _create_filelist_db(newfile=True):
    if newfile or not isfile(join(CFG_ROOT, 'filelist.db')):
        if isfile(join(CFG_ROOT,'filelist.db')):
            #backup the old file if it is present
            bkname = 'filelist.db.%s' % datetime.now().strftime("%d%b%y.%H%M%S")
            try:
                shutil.move(join(CFG_ROOT, 'filelist.db'), join(CFG_ROOT, bkname))
                logger.info("Backing up old (corrupted?) filelist.db to %s" % bkname)
            except:
                logger.exception("Unable to backup filelist.db")
        if isfile(join(CFG_ROOT, 'filelist.db')):
            logger.warning("Filelist.db still present (???).")
            try:
                os.remove(join(CFG_ROOT, 'filelist.db'))
            except:
                logger.exception("Unable to delete filelist.db.")
                logger.critical("Filesystem Error")
    # try to create a sqlite instance
    try:
        conn = sqlite3.connect(join(CFG_ROOT, 'filelist.db'))
        logger.debug("Connection open to filelist.db.")
        conn.execute(CREATE_FILELIST_TBL)
        logger.debug("CREATE statement executed on filelist.db")
        conn.commit()
        logger.info("filelist.db ready")
    except:
        logger.exception("Cannot connect to filelist.db")
    finally:
        conn.close()