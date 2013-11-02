from django.conf.urls import patterns

# The URLS in this file will select the handlers for websockets.
urlpatterns = patterns('',
    (r'^game/(?P<game_id>\d+)/event/$', 'game.ws_handlers.game_event'),
    (r'^index_event/$', 'game.ws_handlers.index_event'),
)
    