from datetime import datetime
import unittest

from flask import Flask
from werkzeug.wrappers import Response
from flask_webcache.validation import Validation

a = Flask(__name__)
v = Validation()

from testutils import compare_datetimes 

class ValidationTestCase(unittest.TestCase):

    def test_cant_set_etag(self):
        self.assertFalse(v.can_set_etag(Response(x for x in 'foo')))
        self.assertFalse(v.can_set_etag(Response(headers={"ETag": "foo"})))
        self.assertFalse(v.can_set_etag(Response(status=500)))

    def test_can_set_etag(self):
        self.assertTrue(v.can_set_etag(Response('foo')))
        self.assertTrue(v.can_set_etag(Response(headers={"Server": "foo"})))
        self.assertTrue(v.can_set_etag(Response(status=200)))

    def test_set_etag(self):
        r = Response('foo')
        v.set_etag(r)
        self.assertEquals(r.headers['etag'], '"acbd18db4cc2f85cedef654fccc4a4d8"')

    def test_if_none_match(self):
        r = Response()
        with a.test_request_context(headers=[("if-none-match", '"foo"')]):
            r.set_etag('foo')
            self.assertTrue(v.if_none_match(r))
            r.status_code = 400
            self.assertFalse(v.if_none_match(r))
            r = Response()
            r.set_etag('bar')
            self.assertFalse(v.if_none_match(r))

    def test_not_modified(self):
        r = Response('foo')
        with a.test_request_context():
            v.return_not_modified_response(r)
        self.assertEquals(r.data, '')
        self.assertEquals(r.status_code, 304)

    def test_not_modified_failure(self):
        r = Response('foo')
        with a.test_request_context(method='PUT'):
            v.return_not_modified_response(r)
        self.assertEquals(r.data, 'foo')
        self.assertEquals(r.status_code, 501)

    def test_date_addition(self):
        r = Response()
        v.add_date_fields(r)
        self.assertTrue(compare_datetimes(r.last_modified, datetime.now()))
        self.assertTrue(compare_datetimes(r.date, datetime.now()))
        self.assertEquals(r.last_modified, r.date)

    def test_date_no_clobber(self):
        r = Response()
        r.date = 0
        r.last_modified = 0
        v.add_date_fields(r)
        self.assertEquals(r.date.year, 1970)
        self.assertEquals(r.last_modified.year, 1970)
