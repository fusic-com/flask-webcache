from __future__ import unicode_literals
from werkzeug.contrib.cache import SimpleCache

from . import storage, validation, handlers, modifiers, utils, recache
modifiers, validation, recache # silence pyflakes etc

def easy_setup(app, cache=None):
    cache = cache or SimpleCache()
    config = storage.Config(
        resource_exemptions = ('/static/',),
        master_salt = utils.make_salt() if app.debug else '',
    )
    handlers.RequestHandler(cache, app, config)
    handlers.ResponseHandler(cache, app, config)
