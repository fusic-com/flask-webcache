import unittest
from datetime import timedelta, datetime
from cPickle import dumps, loads

from flask import Flask, send_file
from werkzeug.wrappers import Response
from werkzeug.datastructures import HeaderSet
from werkzeug.contrib.cache import SimpleCache
from flask_webcache.storage import Config, Metadata, Store, Retrieval
from flask_webcache.storage import (CacheMiss, NoResourceMetadata, NoMatchingRepresentation, NotFreshEnoughForClient,
                                    RecacheRequested)
from flask_webcache.recache import RECACHE_HEADER

from testutils import compare_numbers 
a = Flask(__name__)

class UtilsTestCase(unittest.TestCase):

    def test_config_kwargs(self):
        with self.assertRaises(TypeError):
            Config(foo=1)

    def test_metadata(self):
        def check_metadata(m):
            self.assertEquals(m.salt, 'qux')
            self.assertIn('foo', m.vary)
            self.assertIn('bar', m.vary)
        m = Metadata(HeaderSet(('foo', 'bar')), 'qux')
        check_metadata(m)
        check_metadata(loads(dumps(m)))

class StorageTestCase(unittest.TestCase):

    def setUp(self):
        self.c = SimpleCache()
        self.s = Store(self.c)
        self.r = Retrieval(self.c)

    def test_basic_cachability(self):
        with a.test_request_context('/foo'):
            self.assertFalse(self.s.should_cache_response(Response(x for x in 'foo')))
            self.assertTrue(self.s.should_cache_response(Response(status=204)))
            self.assertFalse(self.s.should_cache_response(Response(status=500)))
            self.assertTrue(self.s.should_cache_response(Response('foo')))
            self.assertTrue(self.s.should_cache_response(Response()))
            r = Response()
            r.vary.add('*')
            self.assertFalse(self.s.should_cache_response(r))
        with a.test_request_context('/foo', method='HEAD'):
            self.assertFalse(self.s.should_cache_response(Response('foo')))
        with a.test_request_context('/foo', method='POST'):
            self.assertFalse(self.s.should_cache_response(Response('foo')))

    def test_cache_control_cachability(self):
        def check_response_with_cache_control(**cc):
            r = Response()
            for k, v in cc.iteritems():
                setattr(r.cache_control, k, v)
            return self.s.should_cache_response(r)
        with a.test_request_context():
            self.assertTrue(check_response_with_cache_control(max_age=10))
            self.assertTrue(check_response_with_cache_control(must_revalidate=True))
            self.assertFalse(check_response_with_cache_control(max_age=0))
            self.assertFalse(check_response_with_cache_control(private=True))
            self.assertFalse(check_response_with_cache_control(no_cache=True))
            self.assertFalse(check_response_with_cache_control(no_store=True))

    def test_expire_cachability(self):
        def check_response_with_expires(dt):
            r = Response()
            r.expires = dt
            return self.s.should_cache_response(r)
        with a.test_request_context():
            self.assertFalse(check_response_with_expires(datetime.utcnow() - timedelta(seconds=1)))
            self.assertTrue(check_response_with_expires(datetime.utcnow() + timedelta(seconds=1)))

    def test_default_cachability(self):
        with a.test_request_context('/foo'):
            self.assertTrue(self.s.should_cache_response(Response()))
        with a.test_request_context('/foo', query_string='?bar'):
            self.assertFalse(self.s.should_cache_response(Response()))

    def test_x_cache_headers(self):
        r = Response()
        self.s.mark_cache_hit(r)
        self.assertEquals(r.headers[self.s.X_CACHE_HEADER], 'hit')
        self.s.mark_cache_miss(r)
        self.assertEquals(r.headers[self.s.X_CACHE_HEADER], 'miss')

    def test_metadata_miss(self):
        with self.assertRaises(NoResourceMetadata):
            with a.test_request_context('/foo'):
                self.r.fetch_metadata()

    def test_response_miss(self):
        with self.assertRaises(NoResourceMetadata):
            with a.test_request_context('/foo'):
                self.r.fetch_response()

    def test_store_retrieve_cycle(self):
        with a.test_request_context('/foo'):
            r = Response('foo')
            self.s.cache_response(r)
            self.assertEquals(len(self.c._cache), 2)
            r2 = self.r.fetch_response()
            self.assertEquals(r.data, r2.data)

    def test_vary_miss(self):
        with a.test_request_context('/foo', headers=(('accept-encoding', 'gzip'),)):
            r = Response('foo')
            r.vary.add('accept-encoding')
            r.content_encoding = 'gzip'
            self.s.cache_response(r)
        with self.assertRaises(NoMatchingRepresentation):
            with a.test_request_context('/foo'):
                self.r.fetch_response()

    def test_invalidation_condition(self):
        with a.test_request_context('/foo', method="PUT"):
            r = Response('foo')
            self.assertTrue(self.s.should_invalidate_resource(r))
            r = Response('foo', status=500)
            self.assertFalse(self.s.should_invalidate_resource(r))
        with a.test_request_context('/foo'):
            r = Response('foo')
            self.assertFalse(self.s.should_invalidate_resource(r))

    def test_invalidation(self):
        with a.test_request_context('/foo'):
            r = Response('foo')
            self.s.cache_response(r)
            self.assertEquals(len(self.c._cache), 2)
        with a.test_request_context('/foo', method="PUT"):
            r = Response('foo')
            self.assertTrue(self.s.should_invalidate_resource(r))
            self.s.invalidate_resource()
            self.assertEquals(len(self.c._cache), 1)
        with self.assertRaises(CacheMiss):
            with a.test_request_context('/foo'):
                self.r.fetch_response()

    def test_master_salt_invalidation(self):
        with a.test_request_context('/foo'):
            r = Response('foo')
            self.s.cache_response(r)
            self.assertEquals(self.r.fetch_response().data, 'foo')
            self.r.config.master_salt = 'newsalt'
            with self.assertRaises(NoMatchingRepresentation):
                self.r.fetch_response()

    def test_request_cache_controls(self):
        with a.test_request_context('/foo'):
            self.assertTrue(self.r.should_fetch_response())
        with a.test_request_context('/foo', method='HEAD'):
            self.assertTrue(self.r.should_fetch_response())
        with a.test_request_context('/foo', method='POST'):
            self.assertFalse(self.r.should_fetch_response())
        with a.test_request_context('/foo', headers=(('cache-control', 'no-cache'),)):
            self.assertFalse(self.r.should_fetch_response())
        with a.test_request_context('/foo', headers=(('pragma', 'no-cache'),)):
            self.assertFalse(self.r.should_fetch_response())
        with a.test_request_context('/foo', headers=(('cache-control', 'max-age=0'),)):
            self.assertFalse(self.r.should_fetch_response())
        with a.test_request_context('/foo', headers=(('cache-control', 'max-age=5'),)):
            self.assertTrue(self.r.should_fetch_response())

    def test_response_freshness_seconds(self):
        # this test is raced; if running it takes about a second, it might fail
        r = Response()
        self.assertEquals(0, self.r.response_freshness_seconds(r))
        r.date = datetime.utcnow()
        self.assertTrue(compare_numbers(self.s.DEFAULT_EXPIRATION_SECONDS,
                                        self.r.response_freshness_seconds(r),
                                        1))
        r.expires = datetime.utcnow() + timedelta(seconds=345)
        self.assertTrue(compare_numbers(345, self.r.response_freshness_seconds(r), 1))
        r.cache_control.max_age=789
        self.assertTrue(compare_numbers(789, self.r.response_freshness_seconds(r), 1))

    def test_min_fresh(self):
        # this test is raced; if running it takes about a second, it might fail
        r = Response()
        r.date = datetime.utcnow() - timedelta(seconds=100)
        r.cache_control.max_age = 200
        f = self.r.response_freshness_seconds(r)
        with a.test_request_context('/foo', headers=(('cache-control', 'min-fresh=50'),)):
            try:
                self.r.verify_response_freshness_or_miss(r, f)
            except CacheMiss:
                self.fail('unexpected CacheMiss on reasonably fresh response')
        with a.test_request_context('/foo', headers=(('cache-control', 'min-fresh=150'),)):
            self.assertRaises(NotFreshEnoughForClient, self.r.verify_response_freshness_or_miss, r, f)

    def test_request_cache_control_disobedience(self):
        c = SimpleCache()
        cfg = Config(request_controls_cache=False)
        s = Store(c, cfg)
        r = Retrieval(c, cfg)
        with a.test_request_context('/foo', headers=(('cache-control', 'no-store'),)):
            self.assertTrue(r.should_fetch_response())
        with a.test_request_context('/foo', headers=(('cache-control', 'no-store'),)):
            self.assertTrue(s.should_cache_response(Response()))
        with a.test_request_context('/foo', headers=(('cache-control', 'no-store'),)):
            self.assertTrue(s.should_cache_response(Response()))
        resp = Response()
        resp.date = datetime.utcnow() - timedelta(seconds=100)
        resp.cache_control.max_age = 200
        with a.test_request_context('/foo', headers=(('cache-control', 'min-fresh=150'),)):
            f = self.r.response_freshness_seconds(resp)
            try:
                r.verify_response_freshness_or_miss(resp, f)
            except CacheMiss:
                self.fail('unexpected CacheMiss when ignoring request cache control')

    def test_sequence_converted_responses(self):
        with a.test_request_context('/foo'):
            r = Response(f for f in 'foo')
            r.make_sequence()
            self.assertFalse(self.s.should_cache_response(r))
            r = send_file(__file__)
            r.make_sequence()
            self.assertFalse(self.s.should_cache_response(r))

class RecacheTestCase(unittest.TestCase):

    def setUp(self):
        self.recached = False
        def dispatcher(salt):
            self.recached = True
        self.c = SimpleCache()
        cfg = Config(preemptive_recache_seconds=10, preemptive_recache_callback=dispatcher)
        self.s = Store(self.c, cfg)
        self.r = Retrieval(self.c, cfg)

    def test_preemptive_recaching_predicate(self):
        m = Metadata(HeaderSet(('foo', 'bar')), 'qux')
        def mkretr(**kwargs):
            return Retrieval(self.c, Config(**kwargs))
        with a.test_request_context('/'):
            self.assertFalse(mkretr(preemptive_recache_seconds=10).should_recache_preemptively(10, m))
            self.assertFalse(mkretr(preemptive_recache_callback=lambda x: 0).should_recache_preemptively(10, m))
            self.assertFalse(self.r.should_recache_preemptively(11, m))
            self.assertTrue(self.r.should_recache_preemptively(10, m))
            self.assertFalse(self.r.should_recache_preemptively(10, m))
            self.c.clear()
            self.assertTrue(self.r.should_recache_preemptively(10, m))

    def test_preemptive_recaching_cache_bypass(self):
        fresh = Response('foo')
        with a.test_request_context('/foo'):
            self.s.cache_response(fresh)
            metadata = self.r.fetch_metadata()
        with a.test_request_context('/foo'):
            cached = self.r.fetch_response()
            self.assertEquals(cached.headers[self.r.X_CACHE_HEADER], 'hit')
        with a.test_request_context('/foo', headers={RECACHE_HEADER: metadata.salt}):
            self.assertRaises(RecacheRequested, self.r.fetch_response)
        with a.test_request_context('/foo', headers={RECACHE_HEADER: 'incorrect-salt'}):
            try:
                self.r.fetch_response()
            except RecacheRequested:
                self.fail('unexpected RecacheRequested for incorrect salt')
