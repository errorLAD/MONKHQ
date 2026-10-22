from django.urls import path
from . import views

urlpatterns = [
    path('webhooks/meta/', views.meta_webhook_view, name='meta_webhook'),
    path('connect/instagram/', views.connect_instagram_view, name='connect_instagram'),
    path('callback/', views.instagram_callback_view, name='instagram_callback'),
    path('deauthorize/', views.meta_deauthorize_view, name='meta_deauthorize'),
    path('data-deletion/', views.meta_data_deletion_view, name='meta_data_deletion'),
    path('deletion-status/', views.meta_deletion_status_view, name='meta_deletion_status'),
    path('publish/', views.instagram_publish_view, name='instagram_publish'),
    path('posts/', views.instagram_posts_list_view, name='instagram_posts_list'),
]
