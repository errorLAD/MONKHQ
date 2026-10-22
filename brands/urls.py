from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.brand_dashboard_view, name='brand_dashboard'),
    path('promotions/', views.brand_promotions_list_view, name='brand_promotions_list'),
    path('promotions/create/', views.brand_promotions_create_view, name='brand_promotions_create'),
    path('promotions/applications/', views.brand_applications_view, name='brand_applications'),
    path('promotions/interested/', views.brand_interested_view, name='brand_interested'),
    path('creators/', views.brand_creators_find_view, name='brand_creators_find'),
    path('campaigns/', views.brand_campaigns_view, name='brand_campaigns'),
    path('products/', views.brand_products_view, name='brand_products'),
    path('orders/', views.brand_orders_view, name='brand_orders'),
    path('revenue/', views.brand_revenue_view, name='brand_revenue'),
    path('analytics/', views.brand_analytics_view, name='brand_analytics'),
    path('ai/', views.brand_ai_view, name='brand_ai'),
    path('inbox/', views.brand_inbox_view, name='brand_inbox'),
    path('linkhub/', views.brand_linkhub_view, name='brand_linkhub'),
    path('billing/', views.brand_billing_view, name='brand_billing'),
    path('settings/', views.brand_settings_view, name='brand_settings'),
]
