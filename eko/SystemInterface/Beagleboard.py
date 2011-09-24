import time
from os.path import exists
import eko.SystemInterface.OSTools as OSTools
import logging
import os
import re

logger = logging.getLogger('eko.SystemInterface.Beagleboard')

def get_dieid():
    # read the kernel command line
    try:
        fh = open('/proc/cmdline')
        cmdline = fh.read()
        fh.close()
    except (OSError, IOError):
        logger.exception("Could not read kernel command line")
        return "FAILSAFE"
    a = re.search(r'(dieid=\w+)', cmdline)
    if a:
        return a.group().split('=')[1]
    else:
        return 'FAILSAFE'

def handle_modprobe_ehcihcd(insert=True):
    if insert:
        command = 'modprobe'
    else:
        command = 'rmmod'
    
    # launch modprobe timeout of 30 seconds
    v = OSTools.polling_popen([command, 'ehci_hcd'], timeout=30.0)
    
    # polling_popen returns False upon failure
    if v:
        (ret, err) = v
    else:
        ret, err = '', ''
    
    # rety 5 times while there is an error
    retry_count = 5
    while err and (retry_count > 0):
        v = OSTools.polling_popen([command, 'ehci_hcd'], timeout=30.0)
        if v:
            ret, err = v
        if ret:
            logger.info("Process %s returned without error" % command)
            break
        retry_count -= 1
        if err:
            logger.error("Unable to excecute %s successfuly (%d left)." % (command, retry_count))
    return (ret, err)

def goto_known_state():
    # kill pppd
    pid = OSTools.pppd_pid()
    if pid != 0:
        OSTools.pppd_terminate(pid)
    
    # call rmmod
    logger.warn("Cleaning up, removed ehci_hcd.")
    OSTools.polling_popen(['rmmod', '-f', 'ehci_hcd'], timeout=30.0)
    
    # remove power from usb hub
    set_gpio_usbhub_power(on=False)
    
def ehci_hcd_loaded():
    # open /proc/modules and see if ehci hcd is loaded.
    fh = open('/proc/modules')
    mods = []
    for l in fh:
        if l is not None:
            mods.append(l.split()[0])
    fh.close()
    if 'ehci_hcd' in mods:
        return True
    else:
        return False

#TODO: CHANGE FOR REVC!!!
def set_gpio_usbhub_power(on=True, revB=False):
    retry_count = 5
    
    if not revB:
        gpio_val = "0" if on else "1"
    else:
        gpio_val = "1" if on else "0"
    
    while retry_count > 0:
        try:
            gpio = open('/sys/class/gpio/gpio210/value', 'wb')
            gpio.write(gpio_val) #!!! Changes from BBXM Rev B to Rev C!!!
            gpio.close()
            time.sleep(5) # sleep for 5 seconds till hub has time to power up
            logger.info("Write %s to GPIO210 is successful." % gpio_val)
            break;
        except (IOError, OSError):
            retry_count -= 1;
            logger.exception("Unable to write to GPIO210. Waiting 10s for retry (%d left)." % retry_count )
            time.sleep(10)
    return
    
def turn_on_usbhub():
    # two stages, first enable GPIO210 then modprobe usb_ehci
    logger.info("Applying power to USB hub controller.")
    
    # set gpio. wait to get a lock if need be.
    set_gpio_usbhub_power(on=True)
            
    handle_modprobe_ehcihcd(insert=True)
    
    # check /dev/ttyUSB0
    time.sleep(5)
    
    #### REMOVE!
    #time.sleep(5)
    #os.popen('usb_modeswitch -v 0x19d2 -p 0x0103 -V 19d2 -P 0x0031 -M 5553424312345679000000000000061b000000020000000000000000000000')
    #time.sleep(5)
    
    retry_count = 5
    while retry_count > 0:
        if exists('/dev/ttyUSB0'):
            logger.info("Modem detected on ttyUSB0!")
            break
        else:
            logger.error("Modem still not detected, %d retry attempts left." % retry_count)
            time.sleep(4)
        retry_count -= 1
    
    return exists('/dev/ttyUSB0')

def turn_off_usbhub():
    # two stages, first enable GPIO210 then modprobe usb_ehci
    logger.info("Removing power from USB hub controller.")
    
    # launch modprobe timeout of 30 seconds
    handle_modprobe_ehcihcd(insert=False)
    
    # turn off the hub
    set_gpio_usbhub_power(on=False)
    
    # verify /dev/ttyUSB0 gone
    time.sleep(5)
    retry_count = 5
    while retry_count > 0:
        if not exists('/dev/ttyUSB0'):
            logger.info("Modem absent, no /dev/ttyUSB0!")
            break
        else:
            logger.error("Modem still detected, %d retry attempts left." % retry_count)
            time.sleep(2)
        retry_count -= 1
    
    return not exists('/dev/ttyUSB0')