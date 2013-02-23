from datetime import datetime
from httplib import OK
import hashlib

from flask import request, g
from werkzeug.datastructures import parse_set_header

from .utils import make_salt

class CacheMiss(Exception):
    pass

class Config(object):
    def __init__(self, **kwargs):
        self.resource_exemptions = set(kwargs.pop('resource_exemptions', ()))
        self.master_salt = kwargs.pop('master_salt', '')
        if kwargs:
            raise TypeError("%s got an unexpected keyword argument %r"
                            % (self.__class__.__name__, kwargs.popitem()[0]))

class Metadata(object):
    def __init__(self, vary, salt):
        self.vary = vary
        self.salt = salt
    def __getstate__(self):
        return self.salt + ':' + self.vary.to_header()
    def __setstate__(self, s):
        self.salt, vary = s.split(':', 1)
        self.vary = parse_set_header(vary)

class Base(object):
    X_CACHE_HEADER = 'X-Cache'
    CACHE_SEPARATOR = ':'
    def __init__(self, cache, config=None):
        self.cache = cache
        self.config = config or Config()
    def request_path_and_query(self):
        if request.query_string:
            return '?'.join((request.path, request.query_string))
        return request.path
    def make_key(self, *bits):
        return self.CACHE_SEPARATOR.join(bits)
    def metadata_cache_key(self):
        return self.make_key('metadata', self.request_path_and_query())
    def response_cache_key(self, metadata):
        ctx = hashlib.md5()
        for header in metadata.vary:
            ctx.update(header + request.headers.get(header, ''))
        ctx.update(metadata.salt)
        ctx.update(self.config.master_salt)
        return self.make_key('representation', ctx.hexdigest(),
                             self.request_path_and_query())
    def get_or_miss(self, key, message):
        result = self.cache.get(key)
        if result is None:
            raise CacheMiss(message)
        return result
    def is_exempt(self):
        for prefix in self.config.resource_exemptions:
            if request.path.startswith(prefix):
                return True
        return False

class Retrieval(Base):
    def fetch_metadata(self):
        key = self.metadata_cache_key()
        return self.get_or_miss(key, 'no resource metadata')
    def fetch_response(self):
        metadata = self.fetch_metadata()
        g.cache_metadata = metadata
        key = self.response_cache_key(metadata)
        response = self.get_or_miss(key, 'no matching representation')
        g.cached_response = True
        return response

class Store(Base):
    DEFAULT_EXPIRATION_SECONDS = 300
    def should_cache_response(self, response):
        if (response.is_streamed or        # theoretically possible
                                           #  but not implemented
            request.method != 'GET' or     # no body to cache with HEAD
            response.status_code != OK or  # see 13.8
            '*' in response.vary):         # see 14.44
            return False
        if 'cache-control' in response.headers: # see 14.9.1
            return (
                'private' not in response.cache_control and
                'no-cache' not in response.cache_control and
                'no-store' not in request.cache_control and
                response.cache_control.max_age
            )
        if 'expires' in response.headers: # see 14.21
            return response.expires > datetime.now()
        if request.args:
            return False # see 13.9
        return True
    def response_expiry_seconds(self, response):
        if response.cache_control.max_age is not None:
            return response.cache_control.max_age
        if response.expires:
            return (response.expires - datetime.now()).total_seconds
        return self.DEFAULT_EXPIRATION_SECONDS
    def get_or_create_metadata(self, response, expiry_seconds):
        try:
            metadata = g.cache_metadata
            # TODO: warn when metadata.vary != response.vary
        except AttributeError:
            metadata = Metadata(response.vary, make_salt())
            self.store_metadata(metadata, expiry_seconds)
        return metadata
    def store_metadata(self, metadata, expiry_seconds):
        key = self.metadata_cache_key()
        self.cache.set(key, metadata, expiry_seconds)
        return metadata
    def store_response(self, metadata, response, expiry_seconds):
        key = self.response_cache_key(metadata)
        response.freeze()
        self.cache.set(key, response, expiry_seconds)
    def cache_response(self, response):
        expiry_seconds = self.response_expiry_seconds(response)
        metadata = self.get_or_create_metadata(response, expiry_seconds)
        self.mark_cache_hit(response)
        self.store_response(metadata, response, expiry_seconds)
    def mark_cache_hit(self, response):
        if self.X_CACHE_HEADER:
            response.headers[self.X_CACHE_HEADER] = 'hit'
    def mark_cache_miss(self, response):
        if self.X_CACHE_HEADER:
            response.headers[self.X_CACHE_HEADER] = 'miss'
    def should_invalidate_resource(self, response):
        if response.status[0] not in '23':
            return False
        if request.method in {"GET", "HEAD"}:
            return False
        return True # see 13.10
    def invalidate_resource(self):
        self.cache.delete(self.metadata_cache_key())
