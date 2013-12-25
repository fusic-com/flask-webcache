#!/usr/bin/env python
"""
sleepycalc - an Ajax based calculator meant to demonstrate flask-webcache

sleepycalc is a simple webapp that lets you do basic addition calculations from the browser. The website's frontend
component is a small HTML page with some Javascript to send a form to an HTTP endpoint and display the result. The
website's backend is a single HTTP endpoint that receives two terms and returns their sum. So, for example, if
your sleepycalc is running on localhost:5000, you could GET http://localhost:5000/addition?term1=5&term2=10 and
get the result (15).

The only "problem" with sleepycalc is that it sleeps for X milliseconds whenever result X is returned (so adding
10+5 will take 15 milliseconds, but 1000+500 will take 15 seconds). In order to speed things up, HTTP caching is
used to get the cached response for calculations that were already made.

As you can read below, we do the following things:
 - Create a werkzeug filesystem cache instance caching in /tmp/.sleepycalc
   (see http://werkzeug.pocoo.org/docs/contrib/cache/ for more useful cache implementations)
 - Use flask.ext.webcache.easy_setup to initialize webcache on our app
       flask-webcache requires the installation of two handlers: the RequestHandler and the ResponseHandlers.
       easy_setup will install both at once (try reading easy_setup()'s code, it's trivial); some complex scenario
       may want to insert a different handler (your own, or another extension's) between the request handler and
       the response handler. If you're not sure whether or not you need this, you probably don't.
 - Use the flask.ext.webcache.modifiers.cache_for decorator to add caching headers for /addition
       Once the extension is installed, it will automatically cache any response who'se headers permit caching.

Consider /addition's headers before the extension:
    % http get localhost:5000/addition\?term1=400\&term2=600
    HTTP/1.0 200 OK
    Content-Length: 4
    Content-Type: text/plain
    Date: Wed, 25 Dec 2013 20:52:53 GMT
    Server: Werkzeug/0.9.4 Python/2.7.5+

    1000

vs. after the extension:
    % http get localhost:5000/addition\?term1=400\&term2=600
    HTTP/1.0 200 OK
    Cache-Control: max-age=30
    Content-Length: 4
    Content-Type: text/plain
    Date: Wed, 25 Dec 2013 20:52:36 GMT
    ETag: "a9b7ba70783b617e9998dc4dd82eb3c5"
    Expires: Wed, 25 Dec 2013 20:53:06 GMT
    Last-Modified: Wed, 25 Dec 2013 20:52:36 GMT
    Server: Werkzeug/0.9.4 Python/2.7.5+
    X-Cache: miss

    1000
"""
from httplib import BAD_REQUEST, OK
from time import sleep

from werkzeug.contrib.cache import FileSystemCache

from flask import Flask, render_template, request
from flask.ext.webcache import easy_setup, modifiers

app = Flask(__name__)
werkzeug_cache = FileSystemCache('/tmp/.sleepycalc')
easy_setup(app, werkzeug_cache)

PLAINTEXT = (('Content-Type', 'text/plain'),)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/addition")
@modifiers.cache_for(seconds=30)
def addition():
    try:
        term1, term2 = int(request.args['term1']), int(request.args['term2'])
    except (KeyError, ValueError):
        return 'term1/term2 expected as integer query arguments', BAD_REQUEST, PLAINTEXT
    result = term1 + term2
    sleep(result/1000.0)
    return str(result), OK, PLAINTEXT

if __name__ == '__main__':
    app.run(debug=True)
