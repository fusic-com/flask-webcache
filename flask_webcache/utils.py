from random import getrandbits

def make_salt(bits=128):
    return hex(getrandbits(bits))
