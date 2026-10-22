from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.creator_dashboard_view, name='creator_dashboard'),
    
    # Automations Section
    path('automations/', views.automations_list_view, name='creator_automations_list'),
    path('automations/create/', views.automations_create_view, name='creator_automations_create'),
    path('automations/<uuid:auto_id>/', views.automations_detail_view, name='creator_automations_detail'),
    path('automations/<uuid:auto_id>/pause/', views.automations_pause_view, name='creator_automations_pause'),
    path('automations/<uuid:auto_id>/resume/', views.automations_resume_view, name='creator_automations_resume'),
    path('automations/<uuid:auto_id>/duplicate/', views.automations_duplicate_view, name='creator_automations_duplicate'),
    path('automations/<uuid:auto_id>/test/', views.automations_test_view, name='creator_automations_test'),
    path('automations/<uuid:auto_id>/delete/', views.automations_delete_view, name='creator_automations_delete'),
    path('automations/<uuid:auto_id>/archive/', views.automations_archive_view, name='creator_automations_archive'),
    path('automations/canvas/', views.automations_canvas_view, name='creator_automations_canvas'),
    path('automations/ai-sales/', views.automations_ai_sales_view, name='creator_automations_ai_sales'),
    path('automations/comment-to-dm/', views.automations_comment_to_dm_view, name='creator_automations_comment_to_dm'),
    path('automations/retrigger/', views.automations_retrigger_view, name='creator_automations_retrigger'),
    path('automations/logs/', views.automations_logs_view, name='creator_automations_logs'),
    path('automations/logs/<uuid:exec_id>/', views.automations_execution_detail_view, name='creator_automations_execution_detail'),
    path('automations/analytics/', views.automations_analytics_view, name='creator_automations_analytics'),
    path('automations/templates/', views.automations_templates_view, name='creator_automations_templates'),
    path('automations/templates/<str:template_id>/use/', views.automations_template_use_view, name='creator_automations_template_use'),
    
    # Engagement
    path('engagement/inbox/', views.engagement_inbox_view, name='creator_engagement_inbox'),
    path('engagement/contacts/', views.engagement_contacts_view, name='creator_engagement_contacts'),
    path('engagement/lead-scoring/', views.engagement_lead_scoring_view, name='creator_engagement_lead_scoring'),
    path('engagement/brand-deals/', views.engagement_brand_deals_view, name='creator_engagement_brand_deals'),
    
    # AI Engine
    path('ai/agent/', views.ai_agent_view, name='creator_ai_agent'),
    path('ai/knowledge-base/', views.ai_knowledge_base_view, name='creator_ai_knowledge_base'),
    path('ai/insights/', views.ai_insights_view, name='creator_ai_insights'),
    path('ai/rotation/', views.ai_rotation_view, name='creator_ai_rotation'),
    path('ai/guard/', views.ai_guard_view, name='creator_ai_guard'),
    
    # Promotions
    path('promotions/create/', views.promotions_create_view, name='creator_promotions_create'),
    path('promotions/my/', views.promotions_my_view, name='creator_promotions_my'),
    path('promotions/interested/', views.promotions_interested_view, name='creator_promotions_interested'),
    path('promotions/applications/', views.promotions_applications_view, name='creator_promotions_applications'),
    path('promotions/find/', views.promotions_find_view, name='creator_promotions_find'),
    path('promotions/analytics/', views.promotions_analytics_view, name='creator_promotions_analytics'),
    
    # Link Hub
    path('linkhub/', views.linkhub_main_view, name='creator_linkhub_main'),
    path('linkhub/links/', views.linkhub_links_view, name='creator_linkhub_links'),
    path('linkhub/products/', views.linkhub_products_view, name='creator_linkhub_products'),
    path('linkhub/digital/', views.linkhub_digital_view, name='creator_linkhub_digital'),
    path('linkhub/affiliate/', views.linkhub_affiliate_view, name='creator_linkhub_affiliate'),
    path('linkhub/appearance/', views.linkhub_appearance_view, name='creator_linkhub_appearance'),
    path('linkhub/storefront/', views.linkhub_storefront_view, name='creator_linkhub_storefront'),
    path('linkhub/shortener/', views.linkhub_shortener_view, name='creator_linkhub_shortener'),
    path('linkhub/analytics/', views.linkhub_analytics_view, name='creator_linkhub_analytics'),
    path('linkhub/qrcode/', views.linkhub_qrcode_view, name='creator_linkhub_qrcode'),
    path('linkhub/audience/', views.linkhub_audience_view, name='creator_linkhub_audience'),
    path('linkhub/forms/', views.linkhub_forms_view, name='creator_linkhub_forms'),
    path('linkhub/scheduled/', views.linkhub_scheduled_view, name='creator_linkhub_scheduled'),
    path('linkhub/api/reorder/', views.linkhub_reorder_api, name='creator_linkhub_reorder_api'),
    path('linkhub/api/item/toggle/', views.linkhub_item_toggle_api, name='creator_linkhub_item_toggle_api'),
    path('linkhub/api/item/delete/<uuid:item_id>/', views.linkhub_item_delete_api, name='creator_linkhub_item_delete_api'),
    path('linkhub/item/edit/<uuid:item_id>/', views.linkhub_item_edit_view, name='creator_linkhub_item_edit'),
    path('linkhub/api/item/move/<uuid:item_id>/<str:direction>/', views.linkhub_item_move_api, name='creator_linkhub_item_move_api'),
    path('linkhub/audience/export/', views.linkhub_audience_export_csv, name='creator_linkhub_audience_export'),
    
    # Sales
    path('sales/products/', views.sales_products_view, name='creator_sales_products'),
    path('sales/products/edit/<uuid:product_id>/', views.sales_product_edit_view, name='creator_sales_product_edit'),
    path('sales/products/delete/<uuid:product_id>/', views.sales_product_delete_view, name='creator_sales_product_delete'),
    path('sales/products/add-to-linkhub/<uuid:product_id>/', views.sales_product_add_to_linkhub_view, name='creator_sales_product_add_to_linkhub'),
    path('sales/orders/', views.sales_orders_view, name='creator_sales_orders'),
    path('sales/revenue/', views.sales_revenue_view, name='creator_sales_revenue'),
    
    # Campaigns
    path('campaigns/', views.campaigns_list_view, name='creator_campaigns_list'),
    path('campaigns/coupons/', views.campaigns_coupons_view, name='creator_campaigns_coupons'),
    
    # Developer
    path('developer/api-keys/', views.developer_api_keys_view, name='creator_developer_api_keys'),
    path('developer/webhooks/', views.developer_webhooks_view, name='creator_developer_webhooks'),
    
    # Analytics, Accounts, Billing, Settings
    path('analytics/', views.analytics_view, name='creator_analytics'),
    path('social/', views.social_accounts_view, name='creator_social_accounts'),
    path('health/', views.account_health_view, name='creator_account_health'),
    path('billing/', views.billing_view, name='creator_billing'),
    path('settings/', views.settings_view, name='creator_settings'),

    # Creator Growth Studio (Algrohack-Inspired Features)
    path('growth-studio/', views.growth_studio_overview_view, name='creator_growth_studio_overview'),
    path('growth-studio/scripts/', views.growth_studio_scripts_view, name='creator_script_studio'),
    path('growth-studio/scripts/generate/', views.growth_studio_script_generate_api, name='creator_script_generate_api'),
    path('growth-studio/scripts/regenerate-hooks/', views.growth_studio_script_regenerate_hooks_api, name='creator_script_regenerate_hooks_api'),
    path('growth-studio/content-ideas/generate/', views.growth_studio_content_ideas_api, name='creator_content_ideas_api'),
    path('growth-studio/scripts/<uuid:script_id>/', views.growth_studio_script_detail_view, name='creator_script_detail'),
    path('growth-studio/scripts/<uuid:script_id>/version/', views.growth_studio_script_create_version_view, name='creator_script_create_version'),
    path('growth-studio/scripts/<uuid:script_id>/delete/', views.growth_studio_script_delete_view, name='creator_script_delete'),
    path('growth-studio/viral-finder/', views.growth_studio_viral_finder_view, name='creator_viral_finder'),
    path('growth-studio/viral-finder/import/', views.growth_studio_viral_import_view, name='creator_viral_import'),
    path('growth-studio/viral-finder/<uuid:video_id>/analyze/', views.growth_studio_viral_analyze_view, name='creator_viral_analyze'),
    path('growth-studio/viral-finder/<uuid:video_id>/save/', views.growth_studio_viral_save_inspiration_view, name='creator_viral_save_inspiration'),
    path('growth-studio/voice-profile/', views.growth_studio_voice_profile_view, name='creator_voice_profile'),
    path('growth-studio/voice-profile/sample/add/', views.growth_studio_voice_sample_add_view, name='creator_voice_sample_add'),
    path('growth-studio/voice-profile/sample/<uuid:sample_id>/delete/', views.growth_studio_voice_sample_delete_view, name='creator_voice_sample_delete'),
    path('growth-studio/voice-profile/synthesize/', views.growth_studio_voice_synthesize_view, name='creator_voice_synthesize'),
    path('growth-studio/voice-profile/delete/', views.growth_studio_voice_profile_delete_view, name='creator_voice_profile_delete'),

    # 1. Content Idea Generator
    path('growth-studio/content-ideas/', views.growth_studio_content_ideas_view, name='creator_content_ideas'),
    path('growth-studio/content-ideas/batch-generate/', views.growth_studio_content_ideas_batch_generate_api, name='creator_content_ideas_batch_generate_api'),
    path('growth-studio/content-ideas/save/', views.growth_studio_content_idea_save_api, name='creator_content_idea_save_api'),
    path('growth-studio/content-ideas/<uuid:idea_id>/edit/', views.growth_studio_content_idea_edit_api, name='creator_content_idea_edit_api'),
    path('growth-studio/content-ideas/<uuid:idea_id>/delete/', views.growth_studio_content_idea_delete_api, name='creator_content_idea_delete_api'),
    path('growth-studio/content-ideas/<uuid:idea_id>/favorite/', views.growth_studio_content_idea_toggle_favorite_api, name='creator_content_idea_toggle_favorite_api'),

    # 2. Content Calendar
    path('growth-studio/calendar/', views.growth_studio_calendar_view, name='creator_content_calendar'),
    path('growth-studio/calendar/create/', views.growth_studio_calendar_entry_create_api, name='creator_calendar_entry_create_api'),
    path('growth-studio/calendar/<uuid:entry_id>/edit/', views.growth_studio_calendar_entry_edit_api, name='creator_calendar_entry_edit_api'),
    path('growth-studio/calendar/<uuid:entry_id>/delete/', views.growth_studio_calendar_entry_delete_api, name='creator_calendar_entry_delete_api'),
    path('growth-studio/calendar/<uuid:entry_id>/reschedule/', views.growth_studio_calendar_reschedule_api, name='creator_calendar_reschedule_api'),

    # 3. Inspiration Library
    path('growth-studio/inspiration-library/', views.growth_studio_inspiration_library_view, name='creator_inspiration_library'),
    path('growth-studio/inspiration-library/add/', views.growth_studio_inspiration_add_api, name='creator_inspiration_add_api'),
    path('growth-studio/inspiration-library/<uuid:item_id>/favorite/', views.growth_studio_inspiration_toggle_favorite_api, name='creator_inspiration_toggle_favorite_api'),
    path('growth-studio/inspiration-library/<uuid:item_id>/delete/', views.growth_studio_inspiration_delete_api, name='creator_inspiration_delete_api'),

    # 4. Performance Coach
    path('growth-studio/performance-coach/', views.growth_studio_performance_coach_view, name='creator_performance_coach'),
    path('growth-studio/performance-coach/ai-analyze/', views.growth_studio_performance_coach_ai_analyze_api, name='creator_performance_coach_ai_analyze_api'),
]

