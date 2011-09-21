#!/bin/python

import subprocess
import time
import sys
import logging
import os

import eko.SystemInterface.OSTools as OSTools

#define constants for MCP23008 GPIO pin masks

GPIO_LED_ERR_NET = 0x80
GPIO_LED_ERR_MB = 0x40
GPIO_LED_MBFRAME = 0x20
GPIO_LED_NET = 0x10
GPIO_LED_SYNC = 0x08

GPIO_EN_PWR_PORT1 = 0x02
GPIO_EN_PWR_PORT2 = 0x01

MCP23008_DEFAULT_ADDR = 0x20
MCP23008_IODIR = 0x00
MCP23008_GPIO = 0x09

MCP23008_I2C_PORT = 2

logger = logging.getLogger('eko.DisplayController')

class DisplayController( object ):
	""" Controls LEDs on the EKO datalogger unit via i2c-tools"""
	tbl = { 'neterr' : GPIO_LED_ERR_NET,
				'mberr' : GPIO_LED_ERR_NET,
				'mbfrm' : GPIO_LED_MBFRAME,
				'net' : GPIO_LED_NET,
				'sync' : GPIO_LED_SYNC,
				'all' : 0xF8}
				
	def __init__(self):
		# check if chip is initialised
		try:
			ret, err = self._send_i2cget_read(2, MCP23008_DEFAULT_ADDR, MCP23008_IODIR)
		except TypeError:
			logger.exception("Error calling i2cget.")
			return False
		if err:
			logger.error('i2cget returned an error: \n%s' % err)
		if ret:
			# its going to be in hex, so convert to python
			try:
				byte = int(str(ret), 0)
				if byte != 0x00:
					self.init_leds()
			except:
				logger.exception("Unable to convert i2cget return value to integer (%s)." % ret)
	
	def _send_i2cset_write(self, port, chipadr, register, byte, mask=0):
		"""Converts parameters to strings, and invokes i2cset"""
		i2c_chip = "0x%02x" % int(chipadr)
		i2c_register = "0x%02x" % int(register)
		i2c_byte = "0x%02x" % int(byte)
		
		# the default arguments passed to the function
		# 	-y : no confirmation prompt
		#	PORT : the /dev/i2c-? port number to use
		#	CHIP : chip address
		#	REG : the register to write to
		#	BYTE : the byte of data to write
		args = ['i2cset', '-y', str(port), i2c_chip, i2c_register, i2c_byte]
		
		# A mask is used to select individual leds
		#	the register is read from the chip, and masked by MASK
		if mask:
			i2c_mask = "0x%02x" % int(mask)
		if mask:
			# arm linux i2cset requires the mask as a positional argument
			args.insert(2, '-m')
			args.insert(3, i2c_mask)
		
		return OSTools.polling_popen(args, 5.0)
	
	def _send_i2cget_read(self, port, chipadr, register):
		i2c_chip = '0x%02x' % int(chipadr)
		i2c_register = '0x%02x' % int(register)
		args = ['i2cget', '-y', str(port), i2c_chip, i2c_register]
		
		# process open
		return OSTools.polling_popen(args, 5.0)
	
	
	def init_leds(self):
		""" Initialise the MCP23008 as per EKO baseboard V2 specification"""
		logger.info('MCP23008 GPIO direction set to out, all pins low.')
		self._send_i2cset_write(MCP23008_I2C_PORT, MCP23008_DEFAULT_ADDR, MCP23008_IODIR, 0x00)
		self._send_i2cset_write(MCP23008_I2C_PORT, MCP23008_DEFAULT_ADDR, MCP23008_GPIO, 0x00)
	
	def control_led(self, ledname, state=False):
		""" Controls a led """
		
		if ledname in self.tbl.keys():
			ledbit = self.tbl[ledname]
			logger.info('Setting LED (%s) state to (%s)' % (ledname, 'on' if state else 'off'))
			self._send_i2cset_write(MCP23008_I2C_PORT, MCP23008_DEFAULT_ADDR, MCP23008_GPIO, 0xFF if state else 0x00, ledbit)
		else:
			logger.error('Unrecognized LED name: %s' % ledname)
			raise ValueError('No led by name %s' % ledname)
	
	def set_light_bar(self, count):
		map = { 1: GPIO_LED_ERR_NET,
				2: GPIO_LED_ERR_NET | GPIO_LED_ERR_MB,
				3: GPIO_LED_MBFRAME | GPIO_LED_ERR_MB | GPIO_LED_ERR_NET,
				4: GPIO_LED_NET | GPIO_LED_MBFRAME | GPIO_LED_ERR_MB | GPIO_LED_ERR_NET,
				5: GPIO_LED_SYNC | GPIO_LED_NET | GPIO_LED_MBFRAME | GPIO_LED_ERR_MB | GPIO_LED_ERR_NET,}
		self._send_i2cset_write(MCP23008_I2C_PORT, MCP23008_DEFAULT_ADDR, MCP23008_GPIO, 0x00, 0xF8)
		if count == 0:
			return True
		if count > 5:
			count = 5
		self._send_i2cset_write(MCP23008_I2C_PORT, MCP23008_DEFAULT_ADDR, MCP23008_GPIO, 0xFF, map[count])
		return True

if __name__ == '__main__':
	logger2 = logging.getLogger('eko')
	logger2.setLevel(logging.DEBUG)
	ch = logging.StreamHandler()
	ch.setLevel(logging.DEBUG)
	formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	ch.setFormatter(formatter)
	logger2.addHandler(ch)
	
	if len(sys.argv) == 3:
		x = DisplayController()
		x.control_led(sys.argv[1], sys.argv[2] == 'on')
	elif len(sys.argv) == 2:
		x = DisplayController()
		if sys.argv[1] != 'AUTO':
			try:
				num = int(sys.argv[1])
			except:
				logger.exception("BAD VALUE")
				exit(0)				
			x.set_light_bar(num)
		else:
			for i in range(6):
				x.set_light_bar(i)
				time.sleep(0.25)
	else:
		print('Usage: displayctrl.py LEDNAME STATE')
		print('Usage: displayctrl.py COUNT(0..5)')
		print('Usage: displayctrl.py AUTO')
		leds =  DisplayController.tbl.keys()
		print('Valid LEDs: (%s)' % ''.join(['%s ' % led for led in leds]).strip())