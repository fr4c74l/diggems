# Copyright 2013 Fractal Jogos e Tecnologia
# Software under Affero GPL license, see LICENSE.txt

import gevent

from django.core.handlers.wsgi import WSGIRequest
from diggems import settings
from django.core import urlresolvers
from django.db import close_connection
from django.utils import translation

_resolver = urlresolvers.RegexURLResolver(r'^/', settings.WEBSOCKET_URLCONF)
    
# WSGI-like API to match needs of gevent-websocket
def dispatcher(environ, start_response):
    print 'WebSocket connection started.'
    try:
        websocket = environ["wsgi.websocket"]
    except KeyError:
        # Not a WebSocket, someone tried to cheat on us!
        start_response('403 Forbidden', [('Content-Type', 'text/plain')])
        return ('This URL can only handle WebSockets.',)

    request = WSGIRequest(environ)
    (handler_function, function_args, function_kwargs) = _resolver.resolve(request.path_info)

    language = translation.get_language_from_request(request, check_path=False)
    translation.activate(language)
    try:
        handler_function(request, websocket, *function_args, **function_kwargs)
    finally:
        websocket.close()
        close_connection()
