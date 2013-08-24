# Copyright 2013 Fractal Jogos e Tecnologia
# Software under Affero GPL license, see LICENSE.txt

import gevent

from django.core.handlers.wsgi import WSGIRequest
from django.conf import settings

_resolver = urlresolvers.RegexURLResolver(r'^/', ettings.WEBSOCKET_URLCONF)
    
# WSGI-like API to match needs of gevent-websocket
def dispatcher(environ, start_response):
    try:
        websocket = environ["wsgi.websocket"]
    except KeyError:
        # Not a WebSocket, someone tried to cheat on us!
        start_response('403 Forbidden', [('Content-Type', 'text/plain')])
        return ('This path can only handle WebSockets.',)

    request = WSGIRequest(environ)
    (handler_function, function_args, function_kwargs) = _resolver.resolve(request.path_info)

    handler_function(request, websocket, *function_args, **function_kwargs)
