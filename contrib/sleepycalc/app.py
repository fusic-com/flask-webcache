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

This version of the code does NOT contain any caching, I'm submitting it so readers can inspect the code before
caching.
"""
from httplib import BAD_REQUEST, OK
from time import sleep

from flask import Flask, render_template, request

app = Flask(__name__)

PLAINTEXT = (('Content-Type', 'text/plain'),)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/addition")
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
