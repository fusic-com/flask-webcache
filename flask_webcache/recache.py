from flask import request, current_app
from werkzeug.http import Headers

RECACHE_HEADER = 'X-Webcache-Recache'

def get_dispatch_args(app_factory, salt):
    headers = Headers(request.headers)
    headers[RECACHE_HEADER] = salt
    return (app_factory, request.method, request.path, request.query_string,
            headers)

def make_rq_dispatcher(queue=None, app_factory=None):
    if queue is None:
        from rq import Queue
        queue = Queue()
    def dispatcher(salt):
        args = get_dispatch_args(app_factory, salt)
        queue.enqueue_call(dispatch_request, args=args)
    return dispatcher

def make_thread_dispatcher(app_factory=None):
    from threading import Thread
    def dispatcher(salt):
        args = get_dispatch_args(app_factory, salt)
        thread = Thread(target=dispatch_request, args=args)
        thread.start()
    return dispatcher

PROGRAM = """import sys
from pickle import load
from flask.ext.webcache.recache import dispatch_request
dispatch_request(*load(sys.stdin))"""
def make_process_dispatcher(app_factory=None):
    from pickle import dumps
    import subprocess
    def dispatcher(salt):
        args = get_dispatch_args(app_factory, salt)
        process = subprocess.Popen(
            ['python', '-c', PROGRAM],
            stdin=subprocess.PIPE
        )
        process.stdin.write(dumps(args))
        process.stdin.close()
    return dispatcher

def dispatch_request(app_factory, method, path, query_string, headers):
    app = app_factory() if callable(app_factory) else current_app
    app.test_client().open(
        method = method,
        path = path,
        query_string = query_string,
        headers = headers,
    )
