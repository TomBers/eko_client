from eko.ThirdParty.baseconv import BaseConverter

from os.path import exists

import pickle

import Crypto.PublicKey.RSA as RSA
import Crypto.Hash.MD5 as MD5

def load_RSA():
    if exists('/etc/eko/prikey.pickle'):
        fh = open('/etc/eko/prikey.pickle', 'rb')
        p = pickle.Unpickler(fh)
        key = p.load()
        fh.close()
    else:
        logger.warn("No primary key object!")
    return key

def solve_challenge(challenge):
    baseconv = BaseConverter('0123456789abcdef')
    key = load_RSA()
    if key:
        try:
            signature = key.sign(challenge, "")
            sig_encoded = baseconv.from_decimal(signature[0])
        except:
            logger.exception("Unable to sign challenge with 512bit RSA.")
            return ''
    else:
        return ''
    return sig_encoded
