import os
import sqlite3
import logging

from datetime import datetime
from os.path import join, splitext, exists, isdir, relpath, isfile, split

from os import makedirs

import tempfile

import ConfigParser

import eko.Util.HexEncoding as hexbyte
import eko.Constants as Constants
import eko.Sensors.Processor as Processor

from eko.SystemInterface.DisplayControl import DisplayController

import sys
import serial

import csv
import time

import modbus_tk
import modbus_tk.defines as cst
import modbus_tk.modbus_rtu as modbus_rtu

from modbus_tk.modbus import ModbusFunctionNotSupportedError, ModbusInvalidResponseError, ModbusNotConnectedError, ModbusError


logger = logging.getLogger('eko.ModbusInterface')

#DEFCONFIG = '/etc/eko/sensor_default.cfg'

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
        
        self.disp = DisplayController()
        
        #paths are absolute
        if not isfile(self.configpath):
            raise SensorConfigException(self.configpath, 'File Not Found')
        if not isdir(self.datapath):
            raise SesnsorConfigException(self.datapath, 'Directory Not Found')
        try:
            self.config.readfp(open(Constants.SENSOR_DEFCONFIG))
        except (ConfigParser.Error, IOError, ValueError, TypeError):
            logger.exception("Unable to load default sensor configuration")
        try:
            self.config.read(configpath)
        except (ConfigParser.Error, IOError):
            logger.exception("Unable to sensor config from %s" % self.configpath)
        if not self.config.has_option('DEFAULT', 'name'):
            logger.warn("Config file has no name for sensor, defaulting to filename")
            self.config.set('DEFAULT', 'name', splitext(split(self.configpath)[1])[0])
        logger.info("Configuration for sensor %s loaded" % self.config.get('DEFAULT', 'name'))
        return
    
    def _open_binaryfile(self, sect):
        binpath = join(self.datapath, self.config.get('DEFAULT', 'name'))
        binpath += '-' + sect.lower() + '.data'
        logger.info("Opening binary file %s for append." % binpath)
        try:
            fh = open(binpath, 'ab')
        except IOError, OSError:
            logger.exception("Unable to open bin file.")
            fh.close()
            
        return (fh, binpath)
    
    def _append_binaryfile_data(self, sect, bindata):
        fh, binpath = self._open_binaryfile(sect)
        fh.write(bindata)
        fh.close()
        return binpath
    
    def _open_datafile(self):
        self.filepath = join(self.datapath, self.config.get('DEFAULT', 'name'))
        self.filepath += '.csv'
        logger.info("Opening data file %s for append." % self.filepath)
        if exists(self.filepath):
            self.newfile = False
        else:
            self.newfile = True
            try:
                tmpfh = open(self.filepath, 'w')
                tmpfh.write("# Data file %s\r\n" % self.filepath)
                tmpfh.write("# Created on %s by config %s\r\n" % (datetime.now().strftime("%d%b%Y-%H%M%S"), self.configpath))
            except (IOError, OSError):
                logger.exception("Could not header comments to datafile.")
            finally:
                tmpfh.close()
        try:
            fh = open(self.filepath, 'ab')
        except (IOError, OSError):
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
        fields = ['date']
        for section in self.config.sections():
            if self.config.has_option(section, 'map_col'):
                if self.config.getboolean(section,'map_col'):
                    if self.config.has_option(section, 'col_name'):
                        fields.append(self.config.get(section, 'col_name'))
                    else:
                        fields.append(str(section))
                    logger.debug('Mapping config section to column %s' % section)
        logger.info('Mapped %d columns.' % len(fields))
        return fields
    def _get_sampling_data(self, sect):
        # sampling interval
        if self.config.has_option(sect, 'samp_interval'):
            try:
                samp_i = self.config.getfloat(sect, 'samp_interval')
            except ConfigParser.Error, TypeError:
                samp_i = 2e-5
                logger.exception("samp_interval has bad value.")
        else:
            samp_i = 2e-5
        
        # sampling count
        if self.config.has_option(sect, 'samp_count'):
            try:
                samp_c = self.config.getint(sect, 'samp_count')
            except ConfigParser.Error, TypeError:
                samp_c = 20
                logger.exception("samp_count has bad value.")
        else:
            samp_c = 20
            
        return (samp_c, samp_i)
        
    def _process_config(self):
        sects = self.config.sections()
        sects.sort()
        datarow = {'date': datetime.utcnow().strftime("%d-%m-%YT%H-%M-%S")}
        files = []
        for sect in sects:
            logger.info("Entering config section %s." % sect)
            if self.config.has_option(sect, 'col_name'):
                key = self.config.get(sect, 'col_name')
            else:
                key = str(sect)
            
            output_value = self._process_config_section_mb(sect)
            if self.config.has_option(sect, 'operation'):
                op = self.config.get(sect, 'operation')
            else:
                op = 'str'
            
            samp_c, samp_i = self._get_sampling_data(sect)
            
            if output_value:
                if op == 'rms':
                    output_value = str(Processor.get_rms(output_value))
                elif op == 'avg':
                    output_value = str(Processor.get_avg(output_value))
                elif op == 'binary':
                    output_value = str(Processor.encode_binary(datetime.utcnow(), output_value, samp_c))
                    files.append(self._append_binaryfile_data(sect, output_value))
                else:
                    output_value = str(output_value)
            else:
                output_value = '0'
            
            try:
                datarow[key] = output_value
            except (KeyError, ValueError, TypeError):
                logger.exception("Could not process config section %s." % sect)
            if datarow[key] == False:
                logger.warn("Error potentially occured in getting data for %s." % sect)
            logger.info("Leaving config section %s." % sect)
        logger.info("Making data entry in csv file.")
        try:
            fh = self._open_datafile()
            cols = self._csv_get_columns()
            logger.debug("Columns: %s." % str(cols))
            logger.debug("Data: %s." % str(datarow))
            csvw = csv.DictWriter(fh, cols, extrasaction='ignore')
            if self.newfile:
                csvw.writeheader()
            csvw.writerow(datarow)
        except:
            logger.exception("Could not write data row to csv file.")
        finally:
            fh.close()
        files.append(self.filepath)
        return files
    
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
        except (IOError, ConfigParser.Error):
            logger.warning("Error config file %s, section %s." % (self.configpath, section))
            # fallback on defaults
            portname = '/dev/ttyS1'
            speed = 9600
            timeout = 5.0
        
        if self.config.has_option(section, 'port_num'):
            try:
                port_num = self.config.getint(section, 'port_num')
            except ConfigParser.Error:
                port_num = 0
        else:
            port_num = 3
        
        if port_num > 3:
            port_num = 0
        
        self.disp.switch_port_power(port_num, True)
        time.sleep(0.2)
        self.disp.control_led('mbfrm', True)
        self.disp.control_led('mberr', False)
        
        try:
            ser = serial.Serial(portname, speed, timeout=timeout)
        except (OSError, IOError, serial.SerialException):
            logger.exception("Unable to open serial port %s@%d." % (portname, speed))
            ser.close()
            self.disp.control_led('mbfrm', False)
            self.disp.control_led('mberr', True)
            return False
        
        logger.debug("Took control of serial port %s, speed %d, timeout %d" % (portname, speed, timeout))
        
        # load modbus specific information
        try:
            # function code : 0x03 READ HOLDING, 0x04 READ INPUT, 0x06 WRIE SINGLE
            mb_func = int(self.config.get(section, 'mb_func'), 0)
            mb_start = int(self.config.get(section, 'mb_start'), 0)
            mb_address = int(self.config.get(section, 'mb_addr'), 0)
            # if a read is specified, we add a count
            if self.config.has_option(section, 'mb_count'):
                mb_count = int(self.config.get(section, 'mb_count'), 0)
            else:
                mb_count = 0
            # if a write is specified, we append output_value
            if self.config.has_option(section, 'mb_write'):
                mb_write = int(self.config.get(section, 'mb_write'), 0)
            else:
                mb_write = 0
        except ConfigParser.Error:
            logger.exception("Unable to get data for modbus transaction.")
            ser.close()
            self.disp.control_led('mbfrm', False)
            self.disp.control_led('mberr', True)
            return False
        
        # Create the Modbus Master
        master = modbus_rtu.RtuMaster(ser)
        #master.set_verbose(True)
        master.set_timeout(timeout)
        logger.debug("Function to execute: a:0x%02x, f:0x%02x, s:0x%04x, c:0x%04x, w:0x%04x." % (mb_address, mb_func, mb_start, mb_count, mb_write))
        logger.info("Running modbus function 0x%02x on device 0x%02x" % (mb_func, mb_address))
        try:
            if ((mb_func == cst.READ_HOLDING_REGISTERS) or (mb_func == cst.READ_INPUT_REGISTERS)):
                data = master.execute(mb_address, mb_func, mb_start, mb_count)
                logger.debug('Read Op: return data for 0x%02x fn(0x%02x) is %s.' % (mb_address, mb_func, hexbyte.Int16ToHex(list(data))))
            elif mb_func == cst.WRITE_SINGLE_REGISTER:
                data = master.execute(mb_address, mb_func, mb_start, output_value=mb_write)
                logger.debug('Writing data to 0x%02x: [0x%04x] 0x%02x.' %  (mb_address, mb_start, mb_write))
            else:
                logger.error('Unrecognised function code requested.')
        except (serial.SerialException, ModbusFunctionNotSupportedError,
                ModbusInvalidResponseError, ModbusNotConnectedError,
                ModbusError):
            # exception handler
            self.disp.control_led('mbfrm', False)
            self.disp.control_led('mberr', True)
            logger.exception('Func(0x%02x) on 0x%02x failed.' % (mb_func, mb_address))
            data = False
        time.sleep(0.5)
        ser.close()
        self.disp.control_led('mbfrm', False)
        self.disp.switch_port_power(port_num, False)
        return data
        