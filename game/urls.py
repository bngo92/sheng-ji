from django.conf.urls import patterns, include, url
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^$', 'main.views.home', name='home'),
    url(r'^logout/', 'main.views.logout', name='logout'),
    url(r'^new_game/', 'main.views.new_game', name='new_game'),
    url(r'^draw/', 'main.views.ready', name='draw'),
    url(r'^play/(?P<game_id>\d+)', 'main.views.play', name='play'),
    url(r'^status/(?P<game_id>\d+)', 'main.views.status', name='status'),
    url(r'^game/(?P<game_id>\d+)', 'main.views.game', name='game'),
    url(r'^ready/(?P<game_id>\d+)', 'main.views.ready', name='ready'),
    url(r'^reserve/(?P<game_id>\d+)', 'main.views.reserve', name='reserve'),
    url(r'^rematch/(?P<game_id>\d+)', 'main.views.rematch', name='rematch'),
    # url(r'^game/', include('game.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
