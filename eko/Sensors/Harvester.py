import os
import sqlite3
import logging

from datetime import datetime
from os.path import join, splitext, makedirs, exists, isdir, relpath, isfile, split
import tempfile

import ConfigParser
import hexbyte

import sys
import serial

import csv

import modbus_tk
import modbus_tk.defines as cst
import modbus_tk.modbus_rtu as modbus_rtu

logger = logging.getLogger('eko.Harvester')

DEFCONFIG = '/etc/eko/sensor_default.cfg'

class SensorConfigException( Exception ):
	def __init__(self, filename, err):
		self.filename = filename
		self.err = err
	def __str__(self):
		return "Sensor Config Exception: %s, Reason: %s" % (self.filename, self.err)

class Harvester( object ):
	"""Harvest data from a modbus device"""
	def __init__(self, configpath, datapath):
		self.configpath = configpath
		self.datapath = datapath
		self.config = ConfigParser.SafeConfigParser()
		
		#paths are absolute
		if not isfile(self.configpath):
			raise SensorConfigException(self.configpath, 'File Not Found')
		if not isdir(self.datapath):
			raise SesnsorConfigException(self.datapath, 'Directory Not Found')
		try:
			self.config.readfp(open(DEFCONFIG))
		except:
			logger.exception("Unable to load default sensor configuration")
		try:
			self.config.read(configpath)
		except:
			logger.exception("Unable to sensor config from %s" % self.configpath)
		if not self.config.has_option('DEFAULT', 'name'):
			logger.warn("Config file has no name for sensor, defaulting to filename")
			config.set('DEFAULT', 'name', splitext(split(self.configpath))[0])
		logger.info("Configuration for sensor %s loaded" % self.config.get('DEFAULT', 'name'))
		return
	
	def _open_datafile(self):
		self.filepath = join(self.datapath, self.config.get('DEFAULT', 'name'))
		logger.info("Opening data file %s for append." % self.filepath)
		if exists(self.filepath):
			self.newfile = False
		else:
			self.newfile = True
			try:
				tmpfh = open(self.filepath, 'w')
				tmpfh.write("# Data file %s\r\n" % self.filepath)
				tmpfh.write("# Created on %s by config %s\r\n" % (datetime.now().strftime("%d%b%Y-%H%M%S"), self.configpath))
			except:
				logger.exception("Could not header comments to datafile.")
			finally
				tmpfh.close()
		try:
			fh = open(self.filepath, 'ab')
		except:
			logger.exception("Unable to open datafile for append. (%s)." % self.filepath)
		if not fh:
			(fh, path) = tempfile.mkstemp()
			logger.critical("No datafile, creating temp %s" % path)
			self.filepath = path
		self.fh = fh
		return fh
	
	def _close_datafile(self, filehandle):
		filehandle.close()
	
	def _csv_get_columns(self):
		self.fields = []
		for section in self.config.sections():
			if config.has_option(section, 'map_col'):
				if section.getboolean(section,'map_col'):
					self.fields.append(str(section))
					logger.debug('Mapping config section to column %s' % section)
			logger.info('Mapped %d columns.' % len(self.fields))
	
	def _process_config(self):
		sects = self.config.sections()
		sects.sort()
		datarow = {}
		for sect in sects:
			logger.info("Entering config section %s." % sect)
			if config.has_option(sect, 'map_col'):
				key = config.get(sect, 'map_col')
			else:
				key = str(sect)
			
			try:
				datarow[key] = _process_config_section_mb(sect)
			except:
				logger.exception("Could not process config section %s." % sect)
			if datarow[key] == False:
				logger.warn("Error potentially occured in getting data for %s." % sect)
			logger.info("Leaving config section %s." % sect)
		logger.info("Making data entry in csv file.")
		try:
			fh = self.open_datafile()
			csvw = csv.DictWriter(fh, self.csv_get_columns(), extrasaction='ignore')
			if self.newfile:
				csvw.writeheader()
			csvw.writerow(datarow)
		except:
			logger.exception("Could not write data row to csv file.")
		finally:
			fh.close()
		return self.filepath
	
	def harvest(self):
		try:
			return self._process_config()
		except:
			logger.exception("Unable to process %s." % self.configpath)
			return False
		
	def _process_config_section_mb(self, section):
		# use the config section to open a modbus handle
		logger.info("Processing config section %s." % str(section))
		try:
			portname = self.config.get(section,'serialport')
			speed = self.config.getint(section, 'serialbaud')
			if self.config.has_option(section, 'serialtimeout'):
				timeout = self.config.getint(section, 'serialtimeout')
			else:
				timeout = 5.0
			ser = serial.Serial(portname, speed)
		except:
			logger.exception("Unable to open serial port %s@%d." % (portname, speed))
			ser.close()
			return False
			
		logger.info("Took control of serial port %s, speed %d, timeout %d" % (portname, speed, timeout))
		
		try:
			mb_func = int(self.config.get(section, 'mb_func'), 0)
			mb_start = int(self.config.get(section, 'mb_start'), 0)
			mb_address = int(self.config.get(section, 'mb_addr'), 0)
			if self.config.has_option(section, 'mb_count'):
				mb_count = int(self.config.get(section, 'mb_count'), 0)
			else:
				mb_count = 0
			if self.config.has_option(section, 'mb_write'):
				mb_write = int(self.config.get(section, 'mb_write'), 0)
		except:
			logger.exception("Unable to get data for modbus transaction.")
			ser.close()
			return False
			
		master = modbus_rtu.RtuMaster(ser)
		
		logger.info("Running modbus function 0x%02x on device 0x%02x" % (mb_func, mb_address))
		if ((mb_func == cst.READ_HOLDING_REGISTERS) or (mb_func == cst.READ_INPUT_REGISTERS)):
			try:
				data = master.execute(mb_address, mb_func, mb_start, mb_count)
				logger.debug('Return data for 0x%02x fn(0x%02x): %s.' % (mb_address, mb_func, hexbyte.Int16ToHex(list(data))))
			except:
				logger.exception('Func(0x%02x) on %0x02x failed.' % (mb_func, mb_address))
				data = False
		elif mb_func == cst.WRITE_SINGLE_REGISTER:
			try:
				data = master.execute(mb_address, mb_func, mb_start, output_value=mb_write)
				logger.debug('Writing data to 0x%02x: [0x%04x] 0x%02x.' %  (mb_address, mb_start, mb_write))
			except:
				logger.exception('Func(0x%02x) on %0x02x failed.' % (mb_func, mb_address))
				data = False
		
		ser.close()
		return data
		