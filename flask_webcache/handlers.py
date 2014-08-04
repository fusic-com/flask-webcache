from __future__ import unicode_literals
from flask import g

from . import storage, validation, modifiers

def register_extension(app, name, obj):
    if not hasattr(app, 'extensions'):
        app.extensions = {}
    app.extensions.setdefault('webcache', {})[name] = obj

class RequestHandler(storage.Retrieval):
    def __init__(self, cache, app=None, config=None):
        super(RequestHandler, self).__init__(cache, config)
        if app is not None:
            self.init_app(app)
    def init_app(self, app):
        app.before_request(self.before_request)
        register_extension(app, 'request', self)
    def before_request(self):
        modifiers.setup_for_this_request()
        g.webcache_cached_response = False
        try:
            if self.should_fetch_response() and not self.is_exempt():
                return self.fetch_response()
        except storage.CacheMiss:
            pass

class ResponseHandler(validation.Validation, storage.Store):
    def __init__(self, cache, app=None, config=None):
        storage.Store.__init__(self, cache, config)
        if app is not None:
            self.init_app(app)
    def init_app(self, app):
        app.after_request(self.after_request)
        register_extension(app, 'response', self)
    def after_request(self, response):
        self.add_date_fields(response)
        for modifier in modifiers.after_request:
            modifier(response)
        if self.can_set_etag(response):
            self.set_etag(response)
        if self.if_none_match(response):
            return self.return_not_modified_response(response) or response
        if g.webcache_cached_response:
            return response
        if self.should_cache_response(response) and not self.is_exempt():
            self.cache_response(response)
            self.mark_cache_miss(response)
        elif self.should_invalidate_resource(response):
            self.invalidate_resource()
        return response
