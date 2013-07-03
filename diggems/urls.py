from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView
from game.views import AboutView

urlpatterns = patterns (
    '',
    (r'^game/(?P<game_id>\d+)/move/$', 'game.views.move'),
    (r'^game/(?P<game_id>\d+)/join/$', 'game.views.join_game'),
    (r'^game/(?P<game_id>\d+)/abort/$', 'game.views.abort_game'),
    (r'^game/(?P<game_id>\d+)/$', 'game.views.game'),
    (r'^new_game/$', 'game.views.new_game'),
    (r'^$', 'game.views.index'),
    (r'^fb/channel/', 'game.views.fb_channel'),
    (r'^fb/login/', 'game.views.fb_login'),
    (r'^fb/logout/', 'game.views.fb_logout'),
    (r'^about/', AboutView.as_view()),
    
    # Error views:
    (r'^error/404$', 'django.views.defaults.page_not_found'),
    (r'^error/500$', 'django.views.defaults.server_error'),
 )
