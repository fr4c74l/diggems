from django.conf.urls import patterns

# The URLS in this file will select the handlers for websockets.
urlpatterns = patterns('',
    (r'^game/(?P<game_id>\d+)/event/$', 'game.ws_handlers.game_events'),
    (r'^main_chat/$', 'game.ws_handlers.main_chat'),
)
    