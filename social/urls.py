from django.urls import path
from . import views

urlpatterns = [
    path('webhooks/meta/', views.meta_webhook_view, name='meta_webhook'),
    path('connect/instagram/', views.connect_instagram_view, name='connect_instagram'),
    path('callback/', views.instagram_callback_view, name='instagram_callback'),
]
