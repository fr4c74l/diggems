from django.conf.urls import include, patterns, url
#from django.conf.urls.i18n import i18n_patterns

_in_game = patterns('game.views',
    (r'^move/$', 'move'),
    (r'^join/$', 'join_game'),
    (r'^abort/$', 'abort_game'),
    (r'^claim/$', 'claim_game'),
    (r'^rematch/$', 'rematch'),
    (r'^fb_notify_request/$', 'fb_notify_request'),
    (r'^$', 'game'),
)

_in_fb = patterns('game.views',
    (r'^channel/$', 'fb_channel'),
    (r'^login/$', 'fb_login'),
    (r'^logout/$', 'fb_logout'),
    (r'^cancel_request/$', 'fb_cancel_request')
)

_js_info_dict = {
    'packages': ('game',),
}

urlpatterns = patterns('',
    (r'^game/(?P<game_id>\d+)/', include(_in_game)),
    (r'^new_game/$', 'game.views.new_game'),
    (r'^play_now/$', 'game.views.play_now'),
    (r'^join_any/$', 'game.views.play_now', {'join_only': True}),
    (r'^$', 'game.views.index'),
    (r'^fb/', include(_in_fb)),
    (r'^info/(?P<page>.*)/$', 'game.views.info'),
    (r'^donate/$','game.views.donate'),
    (r'^i18n/', include('django.conf.urls.i18n')),
    (r'^jsi18n/$', 'django.views.i18n.javascript_catalog', _js_info_dict),

    # Error views:
    (r'^error/404$', 'django.views.defaults.page_not_found'),
    (r'^error/500$', 'django.views.defaults.server_error'),
)
