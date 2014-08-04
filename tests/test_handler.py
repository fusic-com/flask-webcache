from __future__ import unicode_literals
import unittest
from six.moves.http_client import NOT_MODIFIED

from flask import Flask
from flask_webcache import easy_setup

class HandlerTestCase(unittest.TestCase):

    def setUp(self):
        self.a = Flask(__name__)
        easy_setup(self.a)
        @self.a.route('/foo')
        def foo():
            return 'bar'

    def test_full_cycle(self):
        first = self.a.test_client().get('/foo')
        second = self.a.test_client().get('/foo')
        self.assertIn('x-cache', first.headers)
        self.assertIn('x-cache', second.headers)
        self.assertEquals(first.headers['x-cache'], 'miss')
        self.assertEquals(second.headers['x-cache'], 'hit')
        self.assertEquals(first.data, second.data)

    def test_not_modified_cached_response(self):
        first = self.a.test_client().get('/foo')
        self.assertIn('etag', first.headers)
        second = self.a.test_client().get('/foo', headers=(("if-none-match", first.headers['etag']),))
        self.assertEquals(second.status_code, NOT_MODIFIED)
