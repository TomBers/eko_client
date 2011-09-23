import subprocess
import time
import sys
import logging
import os
import socket
import fcntl
import struct
import array
import signal
import os.path

logger = logging.getLogger('eko.SystemInterface.OSTools')


def net_get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])

def net_all_interfaces():
    max_possible = 128  # arbitrary. raise if needed.
    bytes = max_possible * 32
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    names = array.array('B', '\0' * bytes)
    outbytes = struct.unpack('iL', fcntl.ioctl(
        s.fileno(),
        0x8912,  # SIOCGIFCONF
        struct.pack('iL', bytes, names.buffer_info()[0])
    ))[0]
    namestr = names.tostring()
    return [namestr[i:i+32].split('\0', 1)[0] for i in range(0, outbytes, 32)]


def polling_popen(args, timeout = 1.0):
    """
    ..  py:function:: polling_popen(args [, timeout=1.0])
    
        Calls a app and waits till it returns or times out. Does not use shell.
        
        :param args: Argument list to pass to Popen.
        :param timeout: Time in seconds to wait for process.
    """
    logger.info('Executing %s with args %s.' % (args[0], ''.join(['%s ' % str(x) for x in args])))
    try:
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except ValueError, e:
        logger.error("Value Error raised when attempting to execute args %s. %s." % (str(args), repr(e)))
        return False
    except OSError, e:
        logger.exception("An error occured while executing args: %s." % str(args))
        return False
    
    # start counting
    strt = time.time()
    
    logger.debug("Process spawned with PID %s." % str(proc.pid))
    
    # a loop waiting for program to return, exists if a timeout occurs
    while True:
        # if proc return code is None, then process is still running
        if proc.poll() is not None:
            logger.debug("Process %s returned after %d seconds." % (args[0], time.time() - strt))
            timeout = False
            break
        # check timeout
        if (time.time() - strt) > timeout:
            logger.warn('Process %s timeout. Called with arguments %s.' % (args[0], str(args)))
            timeout = True
            break
        # sleep 100ms
        time.sleep(0.1)
    
    # check to make sure timeout didnt occur.
    if timeout:
        # Abort
        logger.error("Hung process: %s, with pid: %s" % (args[0], str(proc.pid)))
        #proc.kill()
        try:
            os.kill(proc.pid, signal.SIGTERM)
        except OSError:
            logger.exception("Unable to kill hung process.")
        return False
    (ret, err) = proc.communicate()
    if err:
        logger.error('Process %s failure: \n%s.' % (args[0], err))
    if ret:
        logger.debug('Process %s call complete, returned: %s.' % (args[0], ret))
    return (ret, err)

def pppd_launch():
    args = ['pppd', 'call', 'he220']
    logger.info("Launching pppd, calling peer %s." % args[2])
    if not os.path.exists('/etc/ppp/peers/'+args[2]):
        logger.warn('Peer file for %s is missing.' % args[2])
    try:
        pppd = subprocess.Popen(args, shell=False)
    except ValueError:
        logger.exception('Incorrect args passed to popen.')
    except OSError:
        logger.exception('Unable to launch pppd.')
    
    if pppd:
        # pppd does a fork exec so the pid returned here doesnt mean anything
        return pppd.pid
    else:
        return 0

def pppd_isrunning(pid):
    if os.path.exists('/proc/%d' % pid):
        logger.debug("pppd is running with pid %d." % pid)
        return True
    else:
        logger.debug("pppd is not running with pid %d." % pid)
        return False

def pppd_status():
    try:
        ifaces = net_all_interfaces()
    except (IOError, OSError):
        logger.exception("Unable to get all network interfaces.")
        ifaces = []
    logger.debug('Network interfaces available: %s.' % str(ifaces))
    for iface in ifaces:
        if str(iface).startswith('ppp'):
            logger.info("PPP network interface exists: %s." % str(iface))
            return True
    # no ppp interface
    logger.info("PPP network interface absent.")
    return False

def pppd_pid():
    for line in os.popen('ps xa'):
        fields = line.split()
        pid = fields[0]
        proc = fields[4]
        if proc.split('/')[-1]=='pppd':
            logger.info("Found pppd at pid: %s." % pid)
            return int(pid)
    logger.info("pppd not found in processes.")
    return 0

def pppd_terminate(pid, kill=False):
    if not pppd_isrunning(pid):
        logger.warn('pppd with pid: %d is already gone!' % pid)
        return True
    # send signal.SIGTERM and wait for a second
    retrycount = 7
    while pppd_isrunning(pid) and (retrycount > 0):
        if not kill and (retrycount > 2):
            logger.info('sending SIGTERM to pppd (%d)' % pid)
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                logger.exception("Unable to terminate pppd.")
        else:
            logger.info('sending SIGKILL to pppd (%d)' % pid)
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                logger.exception("Unable to kill pppd.")
        time.sleep(2)
        retrycount -= 1
    if pppd_isrunning(pid):
        logger.warn('pppd has not shut down!')
        return pid
    else:
        return 0
