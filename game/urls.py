import django
import django.views.defaults
from django.conf.urls import include, url
from . import views

_in_game = [
    url(r'^move/$', views.move),
    url(r'^join/$', views.join_game),
    url(r'^abort/$', views.abort_game),
    url(r'^claim/$', views.claim_game),
    url(r'^rematch/$', views.rematch),
    url(r'^fb_notify_request/$', views.fb_notify_request),
    url(r'^$', views.game),
]

_in_fb = [
    url(r'^channel/$', views.fb_channel),
    url(r'^login/$', views.fb_login),
    url(r'^logout/$', views.fb_logout),
    url(r'^cancel_request/$', views.fb_cancel_request),
]

_js_info_dict = {
    'packages': ('game',),
}

urlpatterns = [
    url(r'^game/(?P<game_id>\d+)/', include(_in_game)),
    url(r'^new_game/$', views.new_game),
    url(r'^play_now/$', views.play_now),
    url(r'^join_any/$', views.play_now, {'join_only': True}),
    url(r'^$', views.index),
    url(r'^fb/', include(_in_fb)),
    url(r'^info/(?P<page>.*)/$', views.info),
    url(r'^donate/$', views.donate),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^jsi18n/$', django.views.i18n.javascript_catalog, _js_info_dict, name='javascript-catalog'),

    # Error views:
    url(r'^error/404$', django.views.defaults.page_not_found),
    url(r'^error/500$', django.views.defaults.server_error),
]
