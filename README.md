# flask-webcache

[![Build Status](https://travis-ci.org/fusic-com/flask-webcache.png)](https://travis-ci.org/fusic-com/flask-webcache)


A Flask extension that adds HTTP based caching to Flask apps. This extension aims for relatively strict\* and complete rfc2616 implementation, albeit at its present alpha stage it is far from it. That said, deviation from the standard, in code or even terminology, should be considered a bug and can be filed as such (see *Contribution*, below). For the purposes of flask-webcache related documentation (including and especially this document), a webcache means rfc2616 based and compliant caching. If you're not sure what HTTP based caching means, see *What's HTTP based caching*, below; it also explains how this package differs from many other caching related Flask extensions.

\* Although practicality beats purity.

## Features

1. Set of decorators to facilitate settings webcache related headers (`Expires`, `Cache-Control`, etc)
2. Validation related post-request processing (automatic `ETag` headers, `304 NOT MODIFIED` responses, etc)
3. Werkzeug Cache based caching of responses (like a reverse proxy sitting in front of your app)

## Usage

flask-webcache is typically made of two handlers, the `RequestHandler` and the `ResponseHandler` - each handling requests or responses. The request handler tries to fulfill responses from cache rather than invoking application code (as well as do some setting up). The response handler takes care of adding cache headers to the response (flask-webcache provides some helpers for that, see below), resource validation and response caching (based on the caching headers in the response). You can install both handlers together by calling `flask.ext.webcache.easy_setup()`, or use the mixin classes that make up the request and response handlers to use or customize specific functionality (fairly advanced use).

For most serious websites you'd like to install handlers separately. When installed separately, the order of handler installation is important, as well as what is done between handler installations. There's no magic here - the RequestHandler installs a regular Flask [`@before_request`](http://flask.pocoo.org/docs/api/#flask.Flask.before_request) function and the ResponseHandler uses [`@after_request`](http://flask.pocoo.org/docs/api/#flask.Flask.after_request). This leads to a conceptual flow of "requests handled from top to bottom, responses from bottom to top". For example, here's installation order from a real website:

    import models ; models # must import models before we can init logging, so logging can count queries
    initialize_logging(settings)
    flask_web_cache.RequestHandler(cache, app, web_cache_config)
    import assets ; assets
    import auth ; auth
    import views ; views
    import api ; api
    import admin ; admin
    import system_views ; system_views
    flask_web_cache.ResponseHandler(cache, app, web_cache_config)
    install_gzip_compression(app, skip_contenttype=is_unlikely_to_compress_well)

Without going into the specifics of extensions and hooks in this app, you will intuitively see that cached responses will be logged (because `RequestHandler` is installed "below" logging initialization and requests "come from above") and that cached responses will be stored after compression (because `ResponseHandler` is installed "above" gzip compression and responses "come from below").

You will note that the handlers are passed a `cache` object - this should be a [`werkzeug.contrib.cache`](http://werkzeug.pocoo.org/docs/contrib/cache/) based cache. `flask.ext.webcache.easy_setup()` will create a `SimpleCache` by default, but for anything serious you'll want to pass an instance of a better performing shared backend (like `RedisCache` or `MemcachedCache`).

### Configuration

You can pass a `flask.ext.webcache.storage.Config` object to the handlers to change caching behaviour a bit. Parameters are passed as constructor keyword arguments to the `Config` object. While there's not much to be configured at this time, both options are fairly useful:

* `resource_exemptions`: a set of URL prefixes for which no cache-storage will occur. If you're serving static files with Flask, you almost definitely want to pass your static URLs here.
* `master_salt`: a serialized version of `flask.ext.webcache.storage.Metadata` is stored for every cached resource (if a single resource has more than one cached representation, just one metadata object is stored). This metadata contains the [selecting request-headers](http://tools.ietf.org/html/rfc2616#section-13.6) for that resource and a "salt". The salt is just a bit of randomness mixed into the keys in the cache namespace, making resource invalidation easy (just change the salt of the resource). The 'master salt' is another bit of randomness mixed into *every* resource, making *complete* cache invalidation easy - just change the master salt. By default, the master salt is regenerated every time the code is loaded when in debug mode - so if you're using the debug reloader, your cache is effectively flushed when you change your code. When debug is off, the master salt is fixed to an empty string and has no substantial use.

## What's HTTP based caching?

HTTP has quite a few caching-related features, about which you can read in [this](http://www.mnot.net/cache_docs/) excellent introduction or in HTTP's actual specification ([rfc2616](http://www.ietf.org/rfc/rfc2616.txt)). Ultimately, these features help HTTP origin servers, proxies, gateways and user-agents that implement them know if a request can be served from cache or not. These features make it known what pieces of informations to store, under what conditions and for how long. Furthermore, these features allow user-agents to make conditional or partial requests, as well as allow servers to return partial or even entirely body-less responses. These features are typically used to make the web more performant and scalable, and more seldomly can sometimes be used to implement complex protocol logic (talking about conditional requests here).

Contrast this description with typical 'application cache' solutions. These solutions allow the developer of a piece of software to identify bottlenecks in the program and speed them up by caching the results. For example, an expensive database query can be cached, so subsequent queries will appear faster at the cost of serving somewhat older data. While this can be a good approach in some scenarios, it's not without drawbacks. HTTP caching leverages the caching capabilities and potential worldwide distribution of proxies, gateways and user-agents, which application caches simply can not. Generally speaking, I believe well-designed web application and services should rely on HTTP caching and avoid application specific caching if practical.

## Contribution

flask-webcache was written by Yaniv Aknin (`@aknin`) while working for [www.fusic.com](http://www.fusic.com), and is released as an independent BSD licensed extension maintained privately by Yaniv. If you'd like to contribute to the project, please follow these steps:

1. clone the repository (`git clone git://github.com/fusic-com/flask-webcache.git`; or clone from your fork)
2. create and activate a virtualenv (`virtualenv .venv && source .venv/bin/activate`)
3. install an editable version of the extension (`pip install -e .`)
4. install test requirements (`pip install -r tests/requirements.txt`)
5. run the tests (`nosetests`)
6. make modifications to code, docs and tests
7. re-run the tests (and see they pass)
8. push to github and send a pull request

Naturally, contributions with a pull request are the best kind and most likely to be merged. But don't let that stop you from opening an issue if you aren't sure how to solve a particular problem or if you can't provide a pull request - just open an issue, these are highly appreciated too. As earlier mentioned and in particular, any deviation from rfc2616 should be reported as an issue.

While obviously every Flask extensions relies to some extent on Flask, flask-webcache is especially reliant on Werkzeug, the terrific HTTP/WSGI swiss army knife by Armin Ronacher (also author of Flask).
