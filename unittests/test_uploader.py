import eko.WebService.Uploader as upd
import unittest
import sqlite3
from os.path import join, isfile
from datetime import datetime, timedelta
from eko.Util.DBSetup import CREATE_FILELIST_TBL
import logging

logger = logging.getLogger('eko')
class UploaderTest(unittest.TestCase):

    configpath = 'unittests/config'
    datapath = 'unittests/data'
    zippath = 'unittests/zip'
    def setUp(self):
        # create a small filelist
        con = sqlite3.connect('unittests/config/filelist.db')
        c = con.cursor()
        c.execute(CREATE_FILELIST_TBL)
        c.close()
        con.commit()
        con.close()
        
    def _create_some_unsync(self):
        con = sqlite3.connect('unittests/config/filelist.db')
        c = con.cursor()
        c.execute("DELETE FROM filelist")
        c.execute("insert into filelist (filename, synctime) values (?, ?)", ('unittests/data/a',datetime.utcnow()))
        c.execute("insert into filelist (filename, synctime) values (?, ?)", ('unittests/data/b',datetime.utcnow()-timedelta(hours=2)))
        c.execute("insert into filelist (filename) values (?)", ('unittests/data/c',))
        c.execute("insert into filelist (filename) values (?)", ('unittests/data/d',))
        c.execute("insert into filelist (filename, synctime) values (?, ?)", ('unittests/data/e',datetime.utcnow()-timedelta(hours=3)))
        c.execute("insert into filelist (filename) values (?)", ('unittests/data/f',))
        con.commit()
        c.close()
        con.close()
    
    def _create_all_unsync(self):
        con = sqlite3.connect('unittests/config/filelist.db')
        c = con.cursor()
        c.execute("DELETE FROM filelist")
        c.execute("insert into filelist (filename) values (?)", ('unittests/data/a',))
        c.execute("insert into filelist (filename) values (?)", ('unittests/data/b',))
        c.execute("insert into filelist (filename) values (?)", ('unittests/data/c',))
        c.execute("insert into filelist (filename) values (?)", ('unittests/data/d',))
        c.execute("insert into filelist (filename) values (?)", ('unittests/data/e',))
        c.execute("insert into filelist (filename) values (?)", ('unittests/data/f',))
        con.commit()
        c.close()
        con.close()
    
    def _create_all_sync(self):
        con = sqlite3.connect('unittests/config/filelist.db')
        c = con.cursor()
        c.execute("DELETE FROM filelist")
        c.execute("insert into filelist (filename, synctime) values (?, ?)", ('unittests/data/a',datetime.utcnow()-timedelta(hours=1)))
        c.execute("insert into filelist (filename, synctime) values (?, ?)", ('unittests/data/b',datetime.utcnow()-timedelta(hours=2)))
        c.execute("insert into filelist (filename, synctime) values (?, ?)", ('unittests/data/c',datetime.utcnow()-timedelta(hours=3)))
        c.execute("insert into filelist (filename, synctime) values (?, ?)", ('unittests/data/d',datetime.utcnow()-timedelta(hours=4)))
        c.execute("insert into filelist (filename, synctime) values (?, ?)", ('unittests/data/e',datetime.utcnow()-timedelta(hours=5)))
        c.execute("insert into filelist (filename, synctime) values (?, ?)", ('unittests/data/f',datetime.utcnow()-timedelta(hours=6)))
        con.commit()
        c.close()
        con.close()
    
    def testAllUnSyncLoad(self):
        """Fills filelist with 6 fresh values, checks if they were loaded properly."""
        self._create_all_unsync()
        uploader = upd.DataUploader(self.configpath, self.datapath, self.zippath)
        uploader.get_filelist()
        list = [file[1] for file in uploader.filelist]
        check = ['unittests/data/a', 'unittests/data/b', 'unittests/data/c', 'unittests/data/d', 'unittests/data/e', 'unittests/data/f']
        for c in check:
            self.assertEqual(True, c in list)
    
    def testSomeUnSyncLoad(self):
        """Fills filelist with 6 fresh values, checks if they were loaded properly."""
        self._create_all_unsync()
        uploader = upd.DataUploader(self.configpath, self.datapath, self.zippath)
        uploader.get_filelist()
        list = [file[1] for file in uploader.filelist]
        check = [ 'unittests/data/c', 'unittests/data/d', 'unittests/data/f']
        for c in check:
            self.assertEqual(True, c in list)
    
    def testAllUnSyncInZip(self):
        """Tests to see if zipfile is built."""
        self._create_all_unsync()
        uploader = upd.DataUploader(self.configpath, self.datapath, self.zippath)
        uploader.get_filelist()
        basename = datetime.utcnow().strftime('%d%b%y-%H%M%S.sync')
        filename = basename+'.zip'
        manifest = basename+'.lst'
        ret = uploader.build_zip_file()
        self.assertEqual((join(self.zippath, filename), join(self.zippath, manifest)), ret)
        self.assertEqual(isfile(join(self.zippath, filename)), True)
        self.assertEqual(isfile(join(self.zippath, manifest)), True)
        uploader.update_filelist()
        filelist = self._readfilelist()
        self.assertEqual(filelist, [])
    
    def testSomeUnsyncInZip(self):
        self._create_some_unsync()
        uploader = upd.DataUploader(self.configpath, self.datapath, self.zippath)
        uploader.get_filelist()
        basename = datetime.utcnow().strftime('%d%b%y-%H%M%S.sync')
        filename = basename+'.zip'
        manifest = basename+'.lst'
        ret = uploader.build_zip_file()
        self.assertEqual((join(self.zippath, filename), join(self.zippath, manifest)), ret)
        self.assertEqual(isfile(join(self.zippath, filename)), True)
        self.assertEqual(isfile(join(self.zippath, manifest)), True)
        uploader.update_filelist()
        filelist = self._readfilelist()
        self.assertEqual(filelist, [])
    
    def testNoneInZip(self):
        self._create_all_sync()
        uploader = upd.DataUploader(self.configpath, self.datapath, self.zippath)
        uploader.get_filelist()
        basename = datetime.utcnow().strftime('%d%b%y-%H%M%S.sync')
        filename = basename+'.zip'
        manifest = basename+'.lst'
        self.assertEqual(uploader.filelist, [])
        ret = uploader.build_zip_file()
        self.assertEqual(False, ret)
        uploader.update_filelist()
        filelist = self._readfilelist()
        self.assertEqual(filelist, [])
        
    def _readfilelist(self):
        con = sqlite3.connect('unittests/config/filelist.db')
        c = con.cursor()
        req = c.execute("SELECT * FROM filelist WHERE synctime is NULL")
        list = req.fetchall()
        c.close()
        con.close()
        return list
        
        
if __name__ == '__main__':
    logging.basicConfig()
    logger.setLevel(logging.DEBUG)
    unittest.main()