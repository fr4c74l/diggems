from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns (
    '',
    (r'^game/(?P<game_id>\d+)/move/$', 'diggems.views.move'),
    (r'^game/(?P<game_id>\d+)/join/$', 'diggems.views.join_game'),
    (r'^game/(?P<game_id>\d+)/$', 'diggems.views.game'),
    (r'^$', 'diggems.views.new_game'),
 )
