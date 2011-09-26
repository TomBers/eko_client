import sqlite3
from os.path import join, relpath, isfile, exists
from zipfile import ZipFile, ZIP_DEFLATED
from datetime import datetime
import logging

import os

import eko.Constants as Constants
import eko.SystemInterface.Beagleboard as Beagleboard
from eko.Util.Security import solve_challenge

import eko.Util.HexEncoding as Hex

from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
import urllib2
from uuid import uuid1

import hashlib
import shutil


class DataUploader( object ):
    filelist = []
    logger = logging.getLogger('eko.webservice')
    
    def __init__(self, configpath=Constants.CONFIGPATH, datapath=Constants.DATAPATH, zippath=Constants.ZIPPATH):
        self.configpath = configpath
        self.datapath  = datapath
        self.zippath = zippath
    
    def get_filelist(self, limit=15):
        conn = sqlite3.connect(join(self.configpath,'filelist.db'), detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename, synctime FROM filelist WHERE synctime is NULL LIMIT ?", (limit,))
        list = cursor.fetchall()
        if list is not None:
            self.filelist = list
        else:
            self.filelist = []
        conn.close()
        return len(self.filelist)
    
    def build_zip_file(self):
        basename = datetime.utcnow().strftime('%d%b%y-%H%M%S.sync')
        filename = basename+'.zip'
        manifest = basename+'.lst'
        if len(self.filelist) == 0:
            self.logger.info("No files to sync.")
            return False
        try:
            zf = ZipFile(join(self.zippath, filename), 'w', ZIP_DEFLATED)
            for f in [f[1] for f in self.filelist]:
                if isfile(f):
                    self.logger.debug("Adding %s to zipfile." % f)
                    zf.write(f, relpath(f, self.datapath))
                else:
                    self.logger.warn("Data file %s missing." % f)
            zf.close()
            self.logger.info("Files added to zip file %s" % filename)
        except:
            self.logger.exception("Could not create zip file.")
            return False
        try:
            fh = open(join(self.zippath, manifest), 'wb')
            for f in [f[1] for f in self.filelist]:
                fh.write('%s\n' % f)
            fh.close()
        except:
            self.logger.exception("An error occured while trying to write the manifest.")
        return (join(self.zippath, filename), join(self.zippath, manifest))
    
    def update_filelist(self):
        conn = sqlite3.connect(join(self.configpath, 'filelist.db'), detect_types=sqlite3.PARSE_DECLTYPES)
        c = conn.cursor()
        self.logger.info("Updating filelist.db.")
        for id in [f[0] for f in self.filelist]:
            try:
                self.logger.debug("Updating record for filelist id: %d", id)
                c.execute("UPDATE filelist SET synctime=? WHERE id=?", (datetime.utcnow(), id))
            except sqlite3.Error:
                self.logger.exception("An error occured when updating the filelist.")
        conn.commit()
        conn.close()
    
    def upload_file(self, zipfile, manifest, upload_type='data'):
        register_openers()
        
        # create post vars for encoding
        pvars = {'kiosk-id': Beagleboard.get_dieid(),
                'software_version': Constants.VERSION, 'type': upload_type}
        
        self.logger.debug("Sync variables: %s" % str(pvars))
        # check to see if zipfile exists
        if isfile(zipfile):
            zh = open(zipfile, 'rb')
            pvars['payload'] = zh
        else:
            zh = None
        # check to see if manifest exists
        if isfile(manifest):
            mf = open(manifest, 'rb')
            pvars['manifest'] = mf
        else:
            mf = None
        
        get_target = urllib2.Request(Constants.URLUploadRequest)
        
        try:
            resp_url = urllib2.urlopen(get_target)
            url_targ = resp_url.read().strip()
        except urllib2.URLError:
            self.logger.exception("Unable to get upload link.")
            if zh is not None:
                zh.close()
            if mf is not None:
                mf.close()
            return False
        
        #pvars['reference'] = resp_url.headers['X-eko-challenge']
        datagen, headers = multipart_encode(pvars)
        
        headers['X-eko-challenge'] = resp_url.headers['X-eko-challenge']
        headers['X-eko-signature'] = solve_challenge(resp_url.headers['X-eko-challenge'])
        headers['kiosk-id'] = Beagleboard.get_dieid()
        self.logger.debug("Challenge: %s." % headers['X-eko-challenge'])
        self.logger.debug("Sig: %s." % headers['X-eko-signature'])
        self.logger.debug("Kiosk-id: %s" % headers['kiosk-id'])
        
        upload = urllib2.Request(url_targ, datagen, headers)
        try:
            response = urllib2.urlopen(upload)
        except urllib2.HTTPError, e:
            self.logger.exception("Server error: %s" % str(e.code))
            self.logger.error("Server return val: %s." % e.read())
        except urllib2.URLError:
            self.logger.exception("Unable to upload zip file.")
            response = None
        # close zip files
        if zh is not None:
            zh.close()
        if mf is not None:
            mf.close()
        if response is not None:
            resp = response.read()
            if resp.lower().strip() == "success":
                self.logger.info("File upload sucessful! ref: %s." % resp_url.headers['X-eko-challenge'])
                return resp_url.headers['X-eko-challenge']
            else:
                self.logger.error("Message from server '%s'." % resp.lower().strip())
                return False
        else:
            return False
    
    def create_sync_record(self, zipfile):
        sql = "INSERT INTO synclog (time, payload, size, checksum, files) VALUES (?, ?, ?, ?, ?)"
        try:
            fsize = os.stat(zipfile).st_size
        except OSError:
            fsize = 0
        self.logger.debug("Zipfile %s size %d" % (zipfile, fsize))
        try:
            fh = open(zipfile, 'rb')
            m = hashlib.md5()
            for line in fh:
                m.update(line)
            checksum = m.digest()
        except (OSError, IOError):
            self.logger.exception("Error calculating zip file md5.")
            checkum = ''
        finally:
            if fh is not None:
                fh.close()
        self.logger.debug("Payload checksum: %s." % checksum)
        files = "".join(['%s\n' % f[1] for f in self.filelist])
        values = (datetime.utcnow(), zipfile, fsize, Hex.ByteToHex(checksum), files)
        
        con = sqlite3.connect(join(self.configpath, 'sync.db'), detect_types=sqlite3.PARSE_DECLTYPES)
        c = con.cursor()
        try:
            c.execute(sql, values)
            self.logger.debug("Saved synclog to db.")
        except sqlite3.Error:
            self.logger.exception("Database error.")
        finally:
            c.close()
            con.commit()
            con.close()
        return
    
    def zip_logfiles(self):
        # get /var/log/kern.log
        ###   /var/log/daemon.log
        ###   /home/root/eko.log.1-9
        basename = datetime.utcnow().strftime('%d%b%y-%H%M%S.log')
        filename = basename+'.zip'
        manifest = basename+'.lst'
        files = []
        try:
            shutil.copy('/var/log/kern.log', '/tmp/kern.log.'+basename)
            files.append(('kern.log', '/tmp/kern.log.'+basename))
        except (OSError, IOError, shutil.Error):
            self.logger.exception("Unable to copy kernel log.")
        
        try:
            shutil.copy('/var/log/daemon.log', '/tmp/daemon.log.'+basename)
            files.append(('daemon.log', '/tmp/daemon.log.'+basename))
        except (OSError, IOError, shutil.Error):
            self.logger.exception("Unable to copy daemon log.")
        
        try:
            shutil.copy('/home/root/eko.log', '/tmp/eko.log.'+basename)
            files.append(('eko.log', '/tmp/eko.log.'+basename))
        except (OSError, IOError, shutil.Error):
            self.logger.exception("Unable to copy eko log.")
        
        files.append(('eko.log.1', '/home/root/eko.log.1'))
        files.append(('eko.log.2', '/home/root/eko.log.2'))
        files.append(('eko.log.3', '/home/root/eko.log.3'))
        files.append(('eko.log.4', '/home/root/eko.log.4'))
        
        try:
            zf = ZipFile(join(self.zippath, filename), 'w', ZIP_DEFLATED)
            for fname, fpath in files:
                if isfile(fpath):
                    self.logger.debug("Adding %s to zipfile." % fname)
                    zf.write(fpath, fname)
                else:
                    self.logger.warn("Data file %s missing." % fname)
            zf.close()
            self.logger.info("Files added to zip file %s" % filename)
        except:
            self.logger.exception("Could not create zip file.")
            return False
        try:
            fh = open(join(self.zippath, manifest), 'wb')
            for name, path in files:
                fh.write('%s\n' % path)
            fh.close()
        except:
            self.logger.exception("An error occured while trying to write the manifest.")
        return (join(self.zippath, filename), join(self.zippath, manifest))
        
        