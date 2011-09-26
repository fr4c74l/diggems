from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns (
    '',
    (r'^game/(?P<game_id>\d+)/move/$', 'diggems.views.move'),
    (r'^game/(?P<game_id>\d+)/join/$', 'diggems.views.join_game'),
    (r'^game/(?P<game_id>\d+)/$', 'diggems.views.game'),
    (r'^new_game/$', 'diggems.views.new_game'),
    (r'^$', 'diggems.views.index'),
    (r'^fb/channel/', 'diggems.views.fb_channel'),
    (r'^fb/login/', 'diggems.views.fb_login'),
    (r'^fb/logout/', 'diggems.views.fb_logout'),
 )
