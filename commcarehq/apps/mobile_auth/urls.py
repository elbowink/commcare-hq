from django.conf.urls import url, patterns

urlpatterns = patterns('commcarehq.apps.mobile_auth.views',
    url('^keys/$', 'fetch_key_records', name='key_server_url'),
)