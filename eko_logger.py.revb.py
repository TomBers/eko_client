#!/usr/bin/python
"""
The main logger application
"""
# target device may run Python 2.6 so use optparse vs argparse
import optparse
import logging
import sys
import time
import signal
import socket
import urllib2
import os
import sqlite3

from ConfigParser import ConfigParser

from eko.SystemInterface.DisplayControl import DisplayController

import eko.Util.LogHelper as LogHelper
import eko.Util.DBSetup as DBSetup

from eko.Sensors.Dispatcher import EkoDispatcher

import eko.SystemInterface.OSTools as OSTools

import eko.SystemInterface.Beagleboard as Beagleboard

import eko.WebService.Uploader as Uploader
import eko.WebService.ClientMessages as CMsgs
import eko.WebService.ServerMessages as SMsgs

from eko.ThirdParty import ping

import subprocess

from datetime import datetime, timedelta

VERSION = '2.0'

def handleSIGTERM():
    sys.exit(0)
    
signal.signal(signal.SIGTERM, handleSIGTERM)

class InternetConnectionError(Exception):
    """Raised when there is a catastrophic failure when
       a network connection is attempted"""
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class DataLogger(object):
    datadir = '/data'
    logger = logging.getLogger('eko.DataLogger')
    def __init__(self, cfg):
        config = ConfigParser()
        try:
            config.read(cfg)
        except:
            self.logger.exception("Unable to read config file %s." % cfg)
        
        # try to open the databases
        self.logger.info("Opening databases.")
        try:
            DBSetup.check_databases()
        except (sqlite3.Error, IOError, OSError):
            self.logger.exception("Databases could not be opened.")
        
        self.disp = DisplayController()
        try:
            ## removes all modules, shutsdown hub
            Beagleboard.goto_known_state()
        except (OSError, IOError):
            self.logger.exception("Unable to reset board to default setting.")
    
    def _try_network(self):
        # try ping first
        #try:
        #    self.logger.info("Trying ping for google.com.")
        #    x = ping.do_one('www.google.com', 10000, 1, 8)
        #except socket.error:
        #    self.logger.exception("Ping failed!")
        #    x = None
        google_req = urllib2.Request('http://www.google.com/index.html')
        try:
            self.logger.info("Trying url fetch on google.com")
            x = urllib2.urlopen(google_req, timeout=60)
        except urllib2.URLError:
            self.logger.exception("URL Error, unable to reach google.com")
            x = None
        return x
    
    def ready_internet(self):
        self.logger.info("Attempting to connect to the internet.")
        ## open a pppd instance
        OSTools.pppd_launch()
        
        ## wait for pppd to settle
        time.sleep(5)
        
        retrycount = 5
        while retrycount > 0:
            ## to see if ppp is up
            if OSTools.pppd_status():
                ## ppp is up, try ping
                x = self._try_network()
                if x is not None:
                    self.disp.control_led('net', True)
                    self.disp.control_led('neterr', False)
                    self.logger.info("Ping success.")
                    return True
                else:
                    self.disp.control_led('neterr', True)
                    self.disp.control_led('net', False)
                self.logger.info("Sleeping for 10s.")
                time.sleep(10)
            else:
                # ppp is not up
                ## check if process is running
                ppp_pid = OSTools.pppd_pid()
                if ppp_pid == 0:
                    ## ppp has quit
                    raise InternetConnectionError('pppd unexpectedly quit!')
                else:
                    ## wait 10 seconds, and retry
                    time.sleep(10)
            retrycount -= 1
            self.logger.info("Rechecking network, remaining attempts %d." % retrycount)
        OSTools.pppd_terminate(OSTools.pppd_pid())
        return False
    
    def stop_internet(self):
        self.logger.info("Dropping net connection.")
        self.disp.control_led('net', False)
        return OSTools.pppd_terminate(OSTools.pppd_pid())
    
    def datalog(self):
        # instantiate a harvest dispatcher
        try:
            x = Beagleboard.set_gpio_usbhub_power()
            x = Beagleboard.handle_modprobe_ehcihcd()
        except (OSError, IOError):
            self.logger.exception("Error encountered when attempting to turn on USB Hub.")
            x = False
        time.sleep(10)
        dispatch = EkoDispatcher()
        dispatch.import_configs()
        self.logger.info("Dispatching all sensor polling operations.")
        dispatch.dispatch_all()
        self.logger.info("All sensors polled.")
        try:
            x = Beagleboard.handle_modprobe_ehcihcd(insert = False)
            x = Beagleboard.set_gpio_usbhub_power(on = False)
        except:
            self.logger.exception("Error encountered when attempting to power off USB hub.")
        return
    
    def upload_kiosk_messages(self):
        try:
            CMsgs.transmit_clientmessages()
        except:
            self.logger.exception("Unable to transmit client messages to server.")
            return False
        return True
    
    def _download_server_messages(self):
        messages = SMsgs.get_messages()
        return messages
    
    def service_server_messages(self, ignore_sa=False):
        msgs = self._download_server_messages()
        if not msgs:
            return False
        
        for msg in msgs:
            self.logger.debug("Message %s." % str(msg))
            if 'msg_type' not in msg.keys():
                self.logger.warn("No message type specified.")
                continue
            if 'msg' not in msg.keys():
                self.logger.warn("No message specified.")
                continue
            if msg['msg_type'] == 'STAYALIVE':
                if not ignore_sa:
                    self.stay_alive_routine(msg['msg'])
            elif msg['msg_type'] == 'CMD':
                self._exec_process(msg['msg'])
            elif msg['msg_type'] == 'GIVELOGS':
                res = self.upload_logs()
                CMsgs.add_clientmessage("Logs delivered.", res, "Command parser", datetime.utcnow())
            else:
                self.logger.warn("Unrecogised command.")
        return
        
    def _exec_process(self,message):
        self.logger.info("Executing message from server.")
        self.logger.debug("Command is %s." % message)
        try:
            proc = subprocess.Popen(message, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except:
            self.logger.exception("Subprocess could not be opened.")
            return False
        now = datetime.utcnow()
        start = datetime.utcnow() + timedelta(seconds=240)
        while now < start:
            now = datetime.now()
            if proc.poll() is not None:
                timeout = 0
                break;
            timeout = 1
        if timeout:
            self.logger.error("Process timed out.")
            return False
        ret_tuple = proc.communicate()
        self.logger.debug("Command returns: %s." % str(ret_tuple))
        CMsgs.add_clientmessage("Command Executed:\n%s" % str(ret_tuple), '', "Command Executer", datetime.utcnow())
        return
    
    def stay_alive_routine(self,message_text):
        self.logger.info("Stay Alive for 30 minutes.")
        now = datetime.utcnow()
        stop = now + timedelta(seconds=1800)
        CMsgs.add_clientmessage("Staying Alive.", '', "Command parser", datetime.utcnow())
        while now < stop:
            now = datetime.utcnow()
            time.sleep(60)
            try:
                self.upload_kiosk_messages()
            except:
                self.logger.exception("An error occured when uploading messages.")
            # ignore another call to stay alive
            try:
                self.service_server_messages(ignore_sa=True)
            except:
                self.logger.exception("An error occured when attempting to fetch new orders.")
        CMsgs.add_clientmessage("Going to  die.", '', "Command parser", datetime.utcnow())
        try:
            self.upload_kiosk_messages()
        except:
            self.logger.exception("An error occured when uploading messages.")
        
    def upload_logs(self):
        upd = Uploader.DataUploader()
        ret = upd.zip_logfiles()
        if not ret:
            self.logger.info("Upload task exited. Error or nothing to sync.")
            return False
        (zipfile, manifest) = ret
        res = upd.upload_file(zipfile, manifest, upload_type="logs")
        if res:
            upd.create_sync_record(zipfile)
            return res
        else:
            self.disp.control_led('neterr', True)
    
    def upload_data_messages(self):
        upd = Uploader.DataUploader()
        upd.get_filelist()
        ret = upd.build_zip_file()
        if not ret:
            self.logger.info("Upload task exited. Error or nothing to sync.")
            return False
        (zipfile, manifest) = ret
        res = upd.upload_file(zipfile, manifest)
        if res:
            upd.create_sync_record(zipfile)
            upd.update_filelist()
        else:
            self.disp.control_led('neterr', True)
    
    def netsync(self):
        # open a internet connection
        ## power the modem
        self.disp.control_led('all', False)
        
        try:
            x = Beagleboard.turn_on_usbhub()
        except (OSError, IOError):
            self.logger.exception("Error encountered when attempting to turn on USB Hub.")
            x = False
        
        ### raise error led if hub power failed
        if not x:
            self.disp.control_led('neterr', True)
        
        ## wait for system to settle
        time.sleep(10)
        
        retrycount = 3
        while retrycount > 0:
            try:
                res = self.ready_internet()
            except InternetConnectionError:
                self.logger.exception('Could not dial modem.')
                res = None
            if res is not None:
                break
            self.logger.info("Waiting 30 seconds till next attempt.")
            time.sleep(30)
            retrycount -= 1
            self.logger.info("%d attempts left." % retrycount)
        
        # Assume we have net connectivity by this point.
        
        ## sync time if need be
        os.popen('ntpdate -t 90 0.pool.ntp.org 1.pool.ntp.org 2.pool.ntp.org')
        time.sleep(30)
        
        self.disp.control_led('sync', True)
        try:
            self.upload_kiosk_messages()
        except:
            self.logger.exception("Unable to upload kiosk messages")
            self.disp.control_led('neterr', True)
        
        
        try:
            self.upload_data_messages()
        except:
            self.logger.exception('Network Synchronisation Failed!')
            self.disp.control_led('neterr', True)
        
        try:
            self.service_server_messages()
        except:
            self.logger.exception("Unable to get commands from server.")
        
        
        self.disp.control_led('sync', False)
        # terminate network
        self.stop_internet()
        time.sleep(5)
        
        ## power off the modem
        try:
            Beagleboard.turn_off_usbhub()
        except:
            self.logger.exception("Error encountered when attempting to power off USB hub.")
    
    def run(self):
        # mark
        starttime = datetime.utcnow()
        nextsync = starttime
        while True:
            try:
                self.datalog()
            except KeyboardInterrupt:
                exit(0)
            except:
                self.logger.exception("Unhandled exception!")
            
            self.logger.info("Data logging operation complete.")
            # next poll is scheduled for time nextpoll. If nextpoll is ahead
            # tell beagle to sleep for 10 mins
            self.logger.info("Sleeping for 600 seconds.")
            try:
                os.popen('echo 60 > /debug/pm_debug/wakeup_timer_seconds')
                os.popen('echo mem > /sys/power/state')
            except (IOError, OSError):
                self.logger.exception("Unable to put system to sleep")
            # wait 60 seconds
            time.sleep(20)
            # check if its time for a netsync
            if datetime.utcnow() > nextsync:
                self.netsync()
                # next sync is in 6 hours
                nextsync = datetime.utcnow() + timedelta(minutes=6)
            td = nextsync - datetime.utcnow()
            self.logger.info("Next internet sync is in %.2f minutes." % (td.seconds/60.0))
            
            # loop and sleep
def main():
    run_count = 0
    run_error_threshold = 15
    
    usage = 'usage: %prog [-d] [-v] [-c CONFIG]'
    parser = optparse.OptionParser(usage=usage, version="%prog " + VERSION)
    parser.add_option("-d", "--debug", help="Enable debug output.",
                      action="store_true", dest="debug", default=False)
    parser.add_option("-c", "--config",
                      dest="configfile", default="/etc/eko/eko.conf",
                      metavar="CONFIG", help="Path to configuration file.")
    
    (options, args) = parser.parse_args()
    if options.configfile is not None:
        configfile = options.configfile
    else:
        configfile = '/etc/eko/eko.cfg'
    loglvl_console = logging.DEBUG if options.debug else logging.INFO
    
    logger = LogHelper.getLoggerInstance(verbose_level=loglvl_console)
    
    # create datalogger instance and run it
    while True:
        try:
            logger.info("Executing main code with config %s. Attempt #%d." % (configfile, run_count))
            datalogger = DataLogger(configfile)
            time.sleep(5)
            datalogger.run()
        except KeyboardInterrupt:
            sys.exit(0)
        except:
            run_count += 1
            if run_count > run_error_threshold:
                logger.critical("Too many crashes, exiting.")
                sys.exit(-1)
            logger.exception("DataLogger crashed! Attempting to retry.")
if __name__ == "__main__":
    main()
    
    
  