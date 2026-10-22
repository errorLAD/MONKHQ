from django.urls import path
from . import views

urlpatterns = [
    # Dashboard & Overview
    path('', views.admin_dashboard_view, name='admin_platform_root'),
    path('dashboard/', views.admin_dashboard_view, name='admin_platform_dashboard'),
    path('search/', views.admin_search_view, name='admin_platform_search'),
    
    # Users, Creators & Brands
    path('users/', views.admin_users_view, name='admin_platform_users'),
    path('creators/', views.admin_creators_view, name='admin_platform_creators'),
    path('brands/', views.admin_brands_view, name='admin_platform_brands'),
    path('workspaces/', views.admin_workspaces_view, name='admin_platform_workspaces'),
    
    # Automations & AI Engine
    path('automations/', views.admin_automations_view, name='admin_platform_automations'),
    path('ai-engine/', views.admin_ai_engine_view, name='admin_platform_ai_engine'),
    path('engagement/', views.admin_engagement_view, name='admin_platform_engagement'),
    
    # Marketplace & Links
    path('promotions/', views.admin_promotions_view, name='admin_platform_promotions'),
    path('link-hubs/', views.admin_linkhub_view, name='admin_platform_linkhub'),
    
    # Commerce, Orders & Campaigns
    path('products/', views.admin_products_view, name='admin_platform_products'),
    path('orders/', views.admin_orders_view, name='admin_platform_orders'),
    path('campaigns/', views.admin_campaigns_view, name='admin_platform_campaigns'),
    
    # Social, Subscriptions & Analytics
    path('social/', views.admin_social_view, name='admin_platform_social'),
    path('subscriptions/', views.admin_subscriptions_view, name='admin_platform_subscriptions'),
    path('billing/regional/', views.admin_regional_pricing_view, name='admin_regional_pricing'),
    path('analytics/', views.admin_analytics_view, name='admin_platform_analytics'),
    
    # Developer, Health, Security, Audit & Settings
    path('developer/', views.admin_developer_view, name='admin_platform_developer'),
    path('health/', views.admin_health_view, name='admin_platform_health'),
    path('security/', views.admin_security_view, name='admin_platform_security'),
    path('audit-logs/', views.admin_audit_logs_view, name='admin_platform_audit_logs'),
    path('settings/', views.admin_settings_view, name='admin_platform_settings'),
    
    # Actions & CSV Exporter
    path('export/csv/', views.admin_export_csv_view, name='admin_export_csv'),
    path('impersonate/<uuid:user_id>/', views.admin_impersonate_view, name='admin_impersonate'),
    path('impersonate/exit/', views.admin_impersonate_exit_view, name='admin_impersonate_exit'),
]
