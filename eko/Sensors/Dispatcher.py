import os
import sqlite3
import logging

from datetime import datetime
from os import makedirs
from os.path import join, splitext, exists, isdir
import tempfile

import eko.Constants as Constants

from eko.Sensors.ModbusInterface import Harvester, SensorConfigException

logger = logging.getLogger('eko.Dispatcher')


class EkoDispatcher(object):
    """Dispatches polling calls to sensors synchronously."""
    valid_configs = []
    
    def __init__(self, configpath=Constants.CONFIGPATH, datapath=Constants.DATAPATH, sensorcfgpath=Constants.SENSORPATH):
        self.configpath = configpath
        self.datapath = datapath
        self.sensorcfgpath = sensorcfgpath
        return
    
    def import_configs(self):
        """Import configuration files"""
        self.valid_configs = []
        for root, dirs, files in os.walk(self.sensorcfgpath):
            logger.info("Parsing %s for sensor config files." % root)
            #print files
            files_in_cdir = [filen for filen in files if splitext(filen)[1] == '.cfg']
            
            if files_in_cdir is not None:
                logger.debug("Found %d more sensor config files to parse." % len(files_in_cdir))
                self.valid_configs += [join(root, file) for file in files_in_cdir]
        logger.info("Found %d config files to parse." % len(self.valid_configs))
    
    def dispatch_all(self):
        """Dispatch harvesters for all configs"""
        path = self.create_harvest_session()
        for config in self.valid_configs:
            try:
                d = Harvester(config, path)
            except SensorConfigException:
                logger.exception("Unable to read config file %s." % config)
                continue
            if d is None:
                logger.exception("Could not spawn harvester for config: %s and data path: %s.", (config, path))
                return
            try:
                csv_file = d.harvest()
            except:
                logger.exception("Could not harvest data according to config file %s" % config)
            if csv_file is not None:
                logger.info("Appended new data to file: %s." % csv_file)
                # add entry to sqlite file db
                self.add_to_synclist(csv_file)
    
    def add_to_synclist(self, filenames):
        """Add file to filelist.db"""
        if not filenames:
            logger.info("No files to sync.")
            return
        try:
            con = sqlite3.connect(join(self.configpath, "filelist.db"), detect_types=sqlite3.PARSE_DECLTYPES)
            c = con.cursor()
            for filename in filenames:
                x = c.execute("select * from filelist where filename = ? and synctime is NULL", (filename,))
                if not x.fetchone():
                    c.execute("insert into filelist (filename) values (?)", (filename,))
                    logger.info("Created sync record for data file %s" % filename)
                    con.commit()
        except:
            logger.exception("Could not add file to filelist.")
        finally:
            if c is not None:
                c.close()
            if con is not None:
                con.close()
    
    def create_harvest_session(self):
        """Create folders and lay groundwork for data harvesting"""
        path = self.datapath
        td = datetime.now()
        todays_folder = td.strftime("%d%b%Y")
        if ((td.hour >= 0) and (td.hour < 6)):
            time_segment = "0000-0559"
        elif ((td.hour >= 6) and (td.hour < 12)):
            time_segment = "0600-1159"
        elif ((td.hour >=12) and (td.hour < 18)):
            time_segment = "1200-1759"
        else:
            time_segment = "1800-2359"
        path = join(path, todays_folder, time_segment)
        if (exists(path) and isdir(path)):
            logger.debug("Directory %s already exists." % path)
            return path
        else:
            try:
                makedirs(path)
                logger.info("Created new directory for data: %s." % path)
            except (IOError, OSError):
                logger.exception("unable to create directory: %s." % path)
                path = tempfile.mkdtemp()
                logger.critical("using temporary directory: %s." % path)
        return path