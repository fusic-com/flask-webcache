from random import getrandbits

def make_salt(bits=128):
    return hex(getrandbits(bits))

def effective_max_age(response):
    if response.cache_control.s_maxage is not None:
        return response.cache_control.s_maxage
    if response.cache_control.max_age is not None:
        return response.cache_control.max_age
    return None

def none_or_truthy(v):
    if v is None:
        return True
    return bool(v)
