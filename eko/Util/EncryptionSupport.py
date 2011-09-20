import Crypto.Hash.MD5 as MD5
import Crypto.PublicKey.RSA as RSA
import Crypto.PublicKey.DSA as DSA
import Crypto.PublicKey.ElGamal as ElGamal
import Crypto.Util.number as CUN
import os

plaintext = 'foobar is the new colour of choice'

hash = MD5.new(plaintext).digest()
print(repr(hash))

key = RSA.generate(384, os.urandom)
signature = key.sign(hash, '')

