import os.path
import urllib2


from baseconv import BaseConverter

from Crypto.Hash import MD5
from Crypto.PublicKey import RSA

from datetime import datetime
import time

import pickle

import os


baseconv = BaseConverter('0123456789abcdef')

def load_RSA():
    if os.path.isfile('/etc/eko/prikey.pickle'):
        fh = open('/etc/eko/prikey.pickle', 'rb')
        p = pickle.Unpickler(fh)
        key = p.load()
        fh.close()
        print('*** Found /etc/eko/prikey.pickle ***')
        return key
    else:
        print('*** Generating new key ***')
        return generate_RSA()

def generate_RSA():
    fh = open('/etc/eko/prikey.pickle', 'wb')
    p = pickle.Pickler(fh)
    key = RSA.generate(512, os.urandom)
    p.dump(key)
    fh.close()
    baseconv = BaseConverter('0123456789abcdef')
    fh2 = open('/etc/eko/pubkey.text', 'w')
    fh2.write('Public Key e Parameter\n')
    fh2.write(baseconv.from_decimal(key.publickey().e))
    fh2.write('\nPublic key n Parameter\n')
    fh2.write(baseconv.from_decimal(key.publickey().n))
    fh2.close()
    print "New Key Generated!"
    print "-"*20
    print "pubkey.e : %s" % key.publickey().e
    print ""
    print "pubkey.n : %s" % key.publickey().n
    print "-"*20
    return key

if __name__=="__main__":
    key = load_RSA()
    print('Public Key e Parameter\n')
    print(baseconv.from_decimal(key.publickey().e))
    print('\nPublic key n Parameter\n')
    print(baseconv.from_decimal(key.publickey().n))
    exit(0)