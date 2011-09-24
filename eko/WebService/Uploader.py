import sqlite3
from os.path import join, relpath, isfile, exists
from zipfile import ZipFile, ZIP_DEFLATED
from datetime import datetime
import logging

import os

import eko.Constants as Constants
import eko.SystemInterface.Beagleboard as Beagleboard
from eko.Util.Security import solve_challenge

from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
import urllib2
from uuid import uuid1

import hashlib


class DataUploader( object ):
    filelist = []
    logger = logging.getLogger('eko.webservice')
    
    def __init__(self, configpath=Constants.CONFIGPATH, datapath=Constants.DATAPATH, zippath=Constants.ZIPPATH):
        self.configpath = configpath
        self.datapath  = datapath
        self.zippath = zippath
    
    def get_filelist(self, limit=15):
        conn = sqlite3.connect(join(self.configpath,'filelist.db'))
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM filelist WHERE synctime is NULL LIMIT ?", (limit,))
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
        conn = sqlite3.connect(join(self.configpath, 'filelist.db'))
        c = conn.cursor()
        for id in [f[0] for f in self.filelist]:
            try:
                c.execute("UPDATE filelist SET synctime=? WHERE id=?", (datetime.utcnow(), id))
            except sqlite3.Error:
                self.logger.exception("An error occured when updating the filelist.")
        conn.commit()
        conn.close()
    
    def upload_file(self, zipfile, manifest):
        register_openers()
        
        # create post vars for encoding
        pvars = {'kiosk-id': Beagleboard.get_dieid(),
                'software_version': '1.0.0', 'type':'data', 'reference': uuid1().get_hex()}
        
        self.logger.debug("Sync variables: %s" % str(pvars))
        # check to see if zipfile exists
        if isfile(zipfile):
            zh = open(zipfile, 'wb')
            pvars['payload'] = zh
        else:
            zh = None
        # check to see if manifest exists
        if isfile(manifest):
            mf = open(manifest)
            pvars['manifest'] = mf
        else:
            mf = None
        
        datagen, headers = multipart_encode(pvars)
        
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
        
        headers['X-eko-challenge'] = resp_url.headers['X-eko-challenge']
        headers['X-eko-signature'] = solve_challenge(resp_url.headers['X-eko-challenge'])
        
        upload = urllib2.Request(url_targ, datagen, headers)
        try:
            response = urllib2.urlopen(upload)
        except:
            self.logger.exception("Unable to upload zip file.")
        # close zip files
        if zh is not None:
            zh.close()
        if mf is not None:
            mf.close()
        if response is not None:
            resp = response.read()
            if resp == "SUCCESS":
                self.logger.info("File upload sucessful!")
                return True
            else:
                self.logger.error("Message from server %s." % resp)
                return False
        else:
            return False
    
    def create_sync_record(self, zipfile):
        sql = "INSERT INTO synclog (time, payload, size, checksum, files) VALUES (?, ?, ?, ?, ?)"
        try:
            fsize = os.stat(zipfile).st_size
        except OSError:
            fsize = 0
        try:
            fh = open(zipfile, 'rb')
            m = hashlib.md5()
            for line in fh:
                m.update(line)
            checksum = m.digest()
        except OSError, IOError:
            self.logger.exception("Error calculating zip file md5.")
            checkum = ''
        finally:
            if fh is not None:
                fh.close()
        files = "".join(['%s\n' % f[1] for f in self.filelist])
        values = (datetime.utcnow(), zipfile, fsize, checksum, files)
        
        con = sqlite3.connect(join(self.configpath, 'filelist.db'))
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