from django.conf.urls import include, patterns
#from django.conf.urls.i18n import i18n_patterns

_in_game = patterns('game.views',
    (r'^move/$', 'move'),
    (r'^join/$', 'join_game'),
    (r'^abort/$', 'abort_game'),
    (r'^claim/$', 'claim_game'),
    (r'^chat/$', 'chat_post'),
    (r'^$', 'game'),
)

_in_fb = patterns('game.views',
    (r'^channel/$', 'fb_channel'),
    (r'^login/$', 'fb_login'),
    (r'^logout/$', 'fb_logout'),
)

js_info_dict = {
    'packages': ('game',),
}

urlpatterns = patterns('',
    (r'^game/(?P<game_id>\d+)/', include(_in_game)),
    (r'^new_game/$', 'game.views.new_game'),
    (r'^$', 'game.views.index'),
    (r'^adhack/(?P<ad_id>\d)/', 'game.views.adhack'),
    (r'^fb/', include(_in_fb)),
    (r'^info/(?P<page>.*)/$', 'game.views.info'),
    (r'^donate/$','game.views.donate'),
    (r'^i18n/', include('django.conf.urls.i18n')),
    (r'^jsi18n/$', 'django.views.i18n.javascript_catalog', js_info_dict),
    (r'^main_chat/$', 'game.views.chat_post'),

    # Error views:
    (r'^error/404$', 'django.views.defaults.page_not_found'),
    (r'^error/500$', 'django.views.defaults.server_error'),
)
