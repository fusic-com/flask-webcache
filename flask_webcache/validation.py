from __future__ import unicode_literals
from datetime import datetime

from six.moves.http_client import NOT_IMPLEMENTED, NOT_MODIFIED, OK
import hashlib

from flask import request, g

class Validation(object):
    def can_set_etag(self, response):
        return not (
            response.is_streamed or
            'etag' in response.headers or
            response.status_code != OK
        )
    def set_etag(self, response):
        response.set_etag(hashlib.md5(response.data).hexdigest())

    def if_none_match(self, response):
        if response.status[0] != '2' and response.status_code != NOT_MODIFIED:
            return False
        etag, weak = response.get_etag()
        return etag in request.if_none_match
    def return_not_modified_response(self, response):
        if request.method not in {"GET", "HEAD"}:
            # HACK: RFC says we MUST NOT have performed this method, but it was
            #        just performed and there's nothing we can do about it.
            #       To handle this request correctly, the application logic
            #        of this app should have made the if-none-match check and
            #        abort() with 412 PRECONDITION_FAILED.
            #       Not sure what to do, I'm opting to return the 5xx status
            #        501 NOT_IMPLEMENTED. Meh.
            if not hasattr(g, 'webcache_ignore_if_none_match'):
                response.status_code = NOT_IMPLEMENTED
            return
        response.data = ''
        response.status_code = NOT_MODIFIED
    def add_date_fields(self, response):
        now = datetime.utcnow() # freeze time for identical dates
        if 'last-modified' not in response.headers:
            response.last_modified = now
        if 'date' not in response.headers:
            response.date = now
