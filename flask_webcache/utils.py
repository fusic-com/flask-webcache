from __future__ import unicode_literals
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

def werkzeug_cache_get_or_add(cache, key, new_obj, expiry_seconds):
    stored_obj = None
    while stored_obj is None:
        cache.add(key, new_obj, expiry_seconds)
        stored_obj = cache.get(key)
    return stored_obj
