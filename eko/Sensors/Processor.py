import math
import time
import struct

import logging

logger = logging.getLogger("eko.Sensors.Processor")

def get_avg(samples):
    x = math.fsum(samples)
    if x:
        bias = (x / (1.0*len(samples)))
    else:
        bias = 0
    return bias

def get_rms(samples):
    samp = list(samples)
    bias = get_avg(samp)
    ms = math.fsum([(x - bias)**2 for x in samp])/(len(samp)*1.0)
    rms = math.sqrt(ms)
    return rms

def encode_binary(date, samples, sample_len):
    if sample_len != len(samples):
        # we rely on each record being fixed size
        return False
    timestamp = time.mktime(date.timetuple())
    try:
        bytes = struct.pack('>'+'H'*sample_len, *samples)
        timebyts = struct.pack('>'+'f', timestamp)
    except struct.error:
        return False
    return bytes+timebyts

def single_value(data):
    if data is None:
        return ''
    if len(data) == 0:
        return ''
    if len(data) > 1:
        logger.warn("Data being discarded!")
    return str(data[0])