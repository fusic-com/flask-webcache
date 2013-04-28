from datetime import datetime
from httplib import OK
import hashlib

from flask import request, g
from werkzeug.datastructures import parse_set_header

from .utils import make_salt, effective_max_age, none_or_truthy
from .recache import RECACHE_HEADER

class CacheMiss(Exception): pass
class NoResourceMetadata(CacheMiss): pass
class NoMatchingRepresentation(CacheMiss): pass
class NotFreshEnoughForClient(CacheMiss): pass
class RecacheRequested(CacheMiss): pass
class LostMetadataRace(Exception): pass

class Config(object):
    def __init__(self, resource_exemptions=(), master_salt='',
                 request_controls_cache=True, preemptive_recache_seconds=0,
                 preemptive_recache_callback=None):
        self.resource_exemptions = resource_exemptions
        self.master_salt = master_salt
        self.request_controls_cache = request_controls_cache
        self.preemptive_recache_seconds = preemptive_recache_seconds
        self.preemptive_recache_callback = preemptive_recache_callback

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
    DEFAULT_EXPIRATION_SECONDS = 300
    def __init__(self, cache, config=None):
        self.cache = cache
        self.config = config or Config()
    def request_path_and_query(self):
        if request.query_string:
            return '?'.join((request.path, request.query_string))
        return request.path
    def make_key(self, *bits):
        return self.CACHE_SEPARATOR.join(bits)
    def make_response_key(self, namespace, metadata):
        ctx = hashlib.md5()
        for header in metadata.vary:
            ctx.update(header + request.headers.get(header, ''))
        ctx.update(metadata.salt)
        ctx.update(self.config.master_salt)
        return self.make_key(namespace, ctx.hexdigest(),
                             self.request_path_and_query())
    def metadata_cache_key(self):
        return self.make_key('metadata', self.request_path_and_query())
    def response_cache_key(self, metadata):
        return self.make_response_key('representation', metadata)
    def recache_cache_key(self, metadata):
        return self.make_response_key('recache', metadata)
    def get_or_miss(self, key, exception):
        result = self.cache.get(key)
        if result is None:
            raise exception()
        return result
    def is_exempt(self):
        for prefix in self.config.resource_exemptions:
            if request.path.startswith(prefix):
                return True
        return False

class Retrieval(Base):
    def should_fetch_response(self):
        if request.method not in {'GET', 'HEAD'}:
            return False
        if self.config.request_controls_cache:
            return (
                'no-cache' not in request.cache_control and
                'no-cache' not in request.pragma and
                none_or_truthy(request.cache_control.max_age)
            )
        # NOTES: "max-stale" is irrelevant; we expire stale representations
        #        "no-transform" is irrelevant; we never transform
        #        we are explicitly allowed to ignore "only-if-cached" (14.9.4)
        return True
    def fetch_metadata(self):
        key = self.metadata_cache_key()
        return self.get_or_miss(key, NoResourceMetadata)
    def fetch_response(self):
        metadata = self.fetch_metadata()
        if request.headers.get(RECACHE_HEADER) == metadata.salt:
            raise RecacheRequested()
        g.webcache_cache_metadata = metadata
        key = self.response_cache_key(metadata)
        response = self.get_or_miss(key, NoMatchingRepresentation)
        freshness = self.response_freshness_seconds(response)
        self.verify_response_freshness_or_miss(response, freshness)
        if self.should_recache_preemptively(freshness, metadata):
            self.config.preemptive_recache_callback(metadata.salt)
        g.webcache_cached_response = True
        return response
    def response_freshness_seconds(self, response):
        now = datetime.utcnow() # freeze time for identical comparisons
        if response.date:
            age = (now - response.date).total_seconds()
        else:
            age = None
        if 'max-age' in response.cache_control and age:
            rv = response.cache_control.max_age - age
        elif response.expires:
            rv = (response.expires - now).total_seconds()
        elif age:
            rv = self.DEFAULT_EXPIRATION_SECONDS - age
        else:
            rv = 0 # should never happen for cached responses
        return max(0, rv)
    def verify_response_freshness_or_miss(self, response, freshness):
        if not self.config.request_controls_cache:
            return
        if 'min-fresh' not in request.cache_control:
            return
        if freshness >= request.cache_control.min_fresh:
            return
        raise NotFreshEnoughForClient()
    def should_recache_preemptively(self, freshness, metadata):
        if self.config.preemptive_recache_callback is None:
            return False
        if self.config.preemptive_recache_seconds < freshness:
            return False
        key = self.recache_cache_key(metadata)
        if self.cache.get(key):
            return False
        salt = make_salt()
        self.cache.add(key, salt, self.config.preemptive_recache_seconds)
        if self.cache.get(key) != salt:
            return False
        return True

class Store(Base):
    def should_cache_response(self, response):
        if (response.is_streamed or # theoretically possible yet unimplemented
            response._on_close or # _on_close hooks are often unpickleable
            request.method != "GET" or # arbitrarily seems safer to me
            str(response.status_code)[0] != '2' or # see 13.4 & 14.9.1
            '*' in response.vary): # see 14.44
            return False
        if (self.config.request_controls_cache and
            'no-store' in request.cache_control):
            return False
        if 'cache-control' in response.headers: # see 14.9.1
            return (
                'private' not in response.cache_control and
                'no-cache' not in response.cache_control and
                'no-store' not in response.cache_control and
                none_or_truthy(effective_max_age(response))
            )
            # FIXME: we ignore field-specific "private" and "no-cache" :(
        if 'expires' in response.headers: # see 14.21
            return response.expires > datetime.utcnow()
        if request.args:
            return False # see 13.9
        return True
    def response_expiry_seconds(self, response):
        if response.cache_control.max_age is not None:
            return response.cache_control.max_age
        if response.expires:
            return (response.expires - datetime.utcnow()).total_seconds()
        return self.DEFAULT_EXPIRATION_SECONDS
    def get_or_create_metadata(self, response, expiry_seconds):
        try:
            metadata = g.webcache_cache_metadata
            # TODO: warn when metadata.vary != response.vary
        except AttributeError:
            metadata = Metadata(response.vary, make_salt())
            self.store_metadata(metadata, expiry_seconds)
        return metadata
    def store_metadata(self, metadata, expiry_seconds):
        key = self.metadata_cache_key()
        self.cache.add(key, metadata, expiry_seconds)
        saved_metadata = self.cache.get(key)
        if saved_metadata.salt != metadata.salt:
            raise LostMetadataRace('someone else stored metadata for this resource before us')
        return metadata
    def store_response(self, metadata, response, expiry_seconds):
        key = self.response_cache_key(metadata)
        response.freeze()
        self.cache.set(key, response, expiry_seconds)
    def cache_response(self, response):
        expiry_seconds = self.response_expiry_seconds(response)
        try:
            metadata = self.get_or_create_metadata(response, expiry_seconds)
        except LostMetadataRace:
            return
        self.mark_cache_hit(response)
        self.store_response(metadata, response, expiry_seconds)
        self.delete_recache_key(metadata)
    def delete_recache_key(self, metadata):
        self.cache.delete(self.recache_cache_key(metadata))
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
