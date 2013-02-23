from datetime import timedelta, datetime
from functools import wraps

from flask import _request_ctx_stack
from werkzeug.datastructures import ResponseCacheControl
from werkzeug.local import LocalProxy

after_request = LocalProxy(lambda: _request_ctx_stack.top.web_cache)

def setup_for_this_request():
    _request_ctx_stack.top.web_cache = []

class BaseModifier(object):
    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwargs):
            self.after_this_request()
            return func(*args, **kwargs)
        return inner
    def after_this_request(self):
        after_request.append(self.modify_response)
    def modify_response(self, response):
        pass

class cache_for(BaseModifier):
    """A single modifier that sets both the Expires header and the max-age
       directive of the Cache-Control header"""
    def __init__(self, **durations):
        self.durations = durations
    def modify_response(self, response):
        delta = timedelta(**self.durations)
        response.cache_control.max_age = int(delta.total_seconds())
        response.expires = datetime.now() + delta

class cache_control(BaseModifier):
    "Modifier that sets arbitrary Cache-Control directives"
    def __init__(self, **kwargs):
        for key, value in kwargs.iteritems():
            if not hasattr(ResponseCacheControl, key):
                raise TypeError('%s got an unexpected keyword argument %r'
                                % (self.__class__.__name__, key))
        self.kwargs = kwargs
    def modify_response(self, response):
        for key, value in self.kwargs.iteritems():
            setattr(response.cache_control, key, value)
