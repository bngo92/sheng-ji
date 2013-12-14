from django.conf.urls import patterns, include, url
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^$', 'main.views.home', name='home'),
    url(r'^register/', 'main.views.register', name='register'),
    url(r'^logout/', 'main.views.logout', name='logout'),
    url(r'^new_game/', 'main.views.new_game', name='new_game'),
    url(r'^draw/', 'main.views.draw', name='draw'),
    url(r'^status/', 'main.views.status', name='status'),
    # url(r'^game/', include('game.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
