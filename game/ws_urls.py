from django.conf.urls import url
from . import ws_handlers

# The URLS in this file will select the handlers for websockets.
urlpatterns = [
    url(r'^game/(?P<game_id>\d+)/event/$', ws_handlers.game_event),
    url(r'^index_event/$', ws_handlers.index_event),
]

