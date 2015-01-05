from __future__ import unicode_literals
from datetime import datetime, timedelta
import unittest

from werkzeug.wrappers import Response
from flask_webcache.modifiers import cache_for, cache_control

from testutils import compare_datetimes 

class ModifiersTestCase(unittest.TestCase):

    def test_cache_for(self):
        m = cache_for(minutes=5)
        r = Response()
        m.modify_response(r)
        self.assertTrue(compare_datetimes(r.expires, datetime.utcnow() + timedelta(minutes=5)))

    def test_two_cache_fors(self):
        m1 = cache_for(minutes=5)
        m2 = cache_for(minutes=3)
        r = Response()
        m1.modify_response(r)
        m2.modify_response(r)
        self.assertTrue(compare_datetimes(r.expires, datetime.utcnow() + timedelta(minutes=3)))

    def test_cache_control(self):
        m = cache_control(public=True)
        r = Response()
        m.modify_response(r)
        self.assertTrue(r.cache_control.public)

    def test_bad_cache_control(self):
        with self.assertRaises(TypeError):
            cache_control(foo=True)

    def test_additive_cache_control(self):
        m = cache_control(public=True)
        r = Response()
        r.cache_control.no_transform=True
        m.modify_response(r)
        self.assertTrue(r.cache_control.public)
        self.assertIn('no-transform', r.cache_control)

    def test_overriding_cache_control(self):
        m = cache_control(public=True)
        r = Response()
        r.cache_control.public=False
        m.modify_response(r)
        self.assertTrue(r.cache_control.public)
