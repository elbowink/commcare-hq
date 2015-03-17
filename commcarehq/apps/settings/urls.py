from django.conf.urls import *

from commcarehq.apps.domain.urls import domain_settings
from commcarehq.apps.cloudcare.urls import settings_urls as cloudcare_settings
from commcarehq.apps.commtrack.urls import settings_urls as commtrack_settings
from commcarehq.apps.products.urls import settings_urls as product_settings
from commcarehq.apps.programs.urls import settings_urls as program_settings
from commcarehq.apps.facilities.urls import settings_urls as facilities_settings
from commcarehq.apps.locations.urls import settings_urls as location_settings

from commcarehq.apps.settings.views import MyAccountSettingsView, DefaultMySettingsView, MyProjectsList, ChangeMyPasswordView

urlpatterns = patterns(
    'commcarehq.apps.settings.views',
    url(r'^$', DefaultMySettingsView.as_view(), name=DefaultMySettingsView.urlname),
    url(r'^settings/$', MyAccountSettingsView.as_view(), name=MyAccountSettingsView.urlname),
    url(r'^projects/$', MyProjectsList.as_view(), name=MyProjectsList.urlname),
    url(r'^password/$', ChangeMyPasswordView.as_view(), name=ChangeMyPasswordView.urlname),
    url(r'^keyboard_shortcuts_config/$', 'keyboard_config', name="keyboard_config"),
)

domain_specific = patterns('',
    url(r'^$', 'commcarehq.apps.settings.views.default', name="settings_default"),
    (r'^users/', include('commcarehq.apps.users.urls')),
    (r'^project/', include(domain_settings)),
    (r'^cloudcare/', include(cloudcare_settings)),
    (r'^commtrack/', include(commtrack_settings)),
    (r'^products/', include(product_settings)),
    (r'^programs/', include(program_settings)),
    (r'^locations/', include(location_settings)),
    (r'^facilities/', include(facilities_settings)),
    url(r'^api/id_mapping/$', 'commcarehq.apps.settings.views.project_id_mapping', name="project_id_mapping")

)

users_redirect = patterns('commcarehq.apps.settings.views',
    (r'^$', 'redirect_users'),
    (r'^(?P<old_url>[\w_\\\/\-]+)/$', 'redirect_users'))

domain_redirect = patterns('commcarehq.apps.settings.views',
    (r'^$', 'redirect_domain_settings'),
    (r'^(?P<old_url>[\w_\\\/\-]+)/$', 'redirect_domain_settings'))
