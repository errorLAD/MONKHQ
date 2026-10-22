from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_hub_view, name='login_hub'),
    path('creator/login/', views.creator_login_view, name='creator_login'),
    path('creator/signup/', views.creator_signup_view, name='creator_signup'),
    path('brand/login/', views.brand_login_view, name='brand_login'),
    path('brand/signup/', views.brand_signup_view, name='brand_signup'),
    path('admin-platform/login/', views.admin_platform_login_view, name='admin_platform_login'),
    path('logout/', views.logout_view, name='logout'),
]
