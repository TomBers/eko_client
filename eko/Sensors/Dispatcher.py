import os
import sqlite3
import logging

from datetime import datetime
from os.path import join, splitext, makedirs, exists, isdir, relpath
import tempfile



logger = logging.getLogger('eko.HarvestDispatch')

CFG_ROOT = '/etc/eko'
SENSOR_CFG_ROOT = '/etc/eko/sensors'
DATA_ROOT = '/data'

class HarvestDispatcher(object):
	"""Dispatches harvesters synchronously to collect data from modbus devices"""
	
	def __init__(self):
		pass
	
	def import_configs(self):
		"""Import configuration files"""
		self.valid_configs = []
		for root, dirs, files in os.walk(SENSOR_CFG_ROOT):
			logger.info("Parsing %s for sensor config files." % root)
			files_in_cdir = [file for file in files if splitext(file) == '.cfg'].sort()
			logger.debug("Found %d more sensor config files to parse." % len(files_in_cdir))
			self.valid_configs += [join(root, file) for file in files_in_cdir]
	
	def dispatch_all(self):
		"""Dispatch harvesters for all configs"""
		path = self.create_harvest_session()
		for config in self.valid_configs:
			try:
				d = Harvester(config, path)
			except:
				logger.exception("Could not spawn harvester for config: %s and data path: %s.", (config, path))
			try:
				csv_file = d.harvest()
			except:
				logger.exception("Could not harvest data according to config file %s" % config)
			if csv_file:
				logger.info("Appended new data to file: %s." % csv_file)
				# add entry to sqlite file db
				self.add_to_synclist(csv_file)
	
	def add_to_synclist(self, filename):
		"""Add file to filelist.db"""
		try:
			con = sqlite3.connect(join(CFG_ROOT, "filelist.db"))
			with con:
				x = con.execute("select * from filelist where (filename, synctime) is (?, ?)", (filename,None,))
				if not x.fetchone():
					con.execute("insert into filelist (filename) values (?)", (filename,))
					logger.info("Created sync record for data file %s" % filename)
		except:
			logger.exception("Could not add file to filelist.")
		finally:
			con.close()
	
	def create_harvest_session(self):
		"""Create folders and lay groundwork for data harvesting"""
		path = DATA_ROOT
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
			except:
				logger.exception("unable to create directory: %s." % path)
				path = tempfile.mkdtemp()
				logger.critical("using temporary directory: %s." % path)
			
		return path

		