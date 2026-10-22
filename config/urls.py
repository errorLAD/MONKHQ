from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from creator import views as creator_views
from linkhub import views as linkhub_views

urlpatterns = [
    path('', creator_views.landing_view, name='home'),
    path('landing/', creator_views.landing_view, name='landing'),
    path('robots.txt', creator_views.robots_txt_view, name='robots_txt'),
    path('sitemap.xml', creator_views.sitemap_xml_view, name='sitemap_xml'),
    path('django-admin/', admin.site.urls),
    
    # Auth & Portals
    path('accounts/', include('accounts.urls')),
    path('creator/', include('creator.urls')),
    path('brand/', include('brands.urls')),
    path('admin-platform/', include('admin_platform.urls')),
    
    # Public LinkHub & Webhooks & API
    path('linkhub/', include('linkhub.urls')),
    path('@<str:username>/', linkhub_views.public_linkhub_view, name='public_profile_at_top'),
    path('go/<slug:slug>/', linkhub_views.short_link_redirect_view, name='short_link_redirect_top'),
    path('social/', include('social.urls')),
    path('developer/', include('developer.urls')),
    path('automations/', include('automations.urls')),
    path('billing/', include('billing.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
