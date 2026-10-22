from django.urls import path
from . import views

urlpatterns = [
    path('u/<str:username>/', views.public_linkhub_view, name='public_linkhub'),
    path('@<str:username>/', views.public_linkhub_view, name='public_linkhub_at'),
    path('go/<slug:slug>/', views.short_link_redirect_view, name='short_link_redirect'),
    path('click/<uuid:item_id>/', views.click_link_view, name='linkhub_click'),
    path('download/<uuid:digital_id>/', views.digital_download_view, name='digital_download'),
    path('submit-lead/<uuid:link_hub_id>/', views.submit_lead_form_view, name='linkhub_submit_lead'),
    path('subscribe/<uuid:link_hub_id>/', views.subscribe_email_view, name='linkhub_subscribe_email'),
]
