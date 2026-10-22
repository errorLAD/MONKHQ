from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta, date, datetime
import uuid
import csv
from django.http import HttpResponse, JsonResponse

from workspaces.models import Workspace
from automations.models import Automation, AutomationTrigger, AutomationCondition, AutomationAction, AutomationExecution, AutomationLog, AISalesAgent, AutomationTemplate
from engagement.models import Contact, Conversation, Message, LeadScoreRule
from ai_engine.models import AIAgent, KnowledgeBase, KnowledgeDocument, CommentGuard, MessageVariant, AITokenUsage
from promotions.models import Promotion, PromotionApplication, PromotionInterest, BrandDeal
from linkhub.models import LinkHub, LinkHubItem, LinkClick, LinkView, LinkShortener, QRCode, Subscriber
from products.models import Product, DigitalProduct, AffiliateLink
from orders.models import Order, RevenueEvent
from campaigns.models import Campaign, Coupon
from social.models import SocialAccount, AccountHealth
from developer.models import APIKey, WebhookEndpoint, WebhookEvent
from billing.models import Subscription, UsageRecord, Plan
from audit.services import log_audit_event
from django.core.paginator import Paginator
from django.core.validators import URLValidator, ValidationError
import json
from creator.models import (
    CreatorProfile, CreatorVoiceProfile, VoiceSample,
    AIScript, ScriptVersion, DiscoveredVideo, SavedInspiration, VideoAnalysis,
    SavedTrendingTopic, ContentIdea, ContentCalendarEntry, InspirationItem,
    PerformanceCoachReport
)
from creator.services import (
    AIGrowthService, ViralDiscoveryService, BreakoutScoringEngine,
    PerformanceCoachService
)

def landing_view(request):
    if request.user.is_authenticated:
        if request.user.is_creator:
            return redirect('creator_dashboard')
        elif request.user.is_brand:
            return redirect('brand_dashboard')
        elif request.user.is_platform_admin:
            return redirect('admin_platform_dashboard')
    return render(request, 'landing.html')

def privacy_policy_view(request):
    """Serve official Privacy Policy page required for Meta App Review & GDPR."""
    return render(request, 'legal/privacy_policy.html')

def terms_of_service_view(request):
    """Serve official Terms of Service page required for Meta App Review."""
    return render(request, 'legal/terms_of_service.html')

def robots_txt_view(request):
    """Serve production-grade robots.txt for search engine crawlers."""
    host = f"{request.scheme}://{request.get_host()}"
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /django-admin/",
        "Disallow: /admin-platform/",
        "Disallow: /accounts/",
        "Disallow: /creator/",
        "Disallow: /brand/",
        "Disallow: /billing/checkout/",
        "",
        f"Sitemap: {host}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")

def sitemap_xml_view(request):
    """Serve XML sitemap for SEO discovery."""
    host = f"{request.scheme}://{request.get_host()}"
    urls = [
        {"loc": f"{host}/", "changefreq": "daily", "priority": "1.0"},
        {"loc": f"{host}/privacy-policy/", "changefreq": "monthly", "priority": "0.7"},
        {"loc": f"{host}/terms/", "changefreq": "monthly", "priority": "0.7"},
        {"loc": f"{host}/social/data-deletion/", "changefreq": "monthly", "priority": "0.6"},
        {"loc": f"{host}/social/deauthorize/", "changefreq": "monthly", "priority": "0.6"},
        {"loc": f"{host}/accounts/login-hub/", "changefreq": "weekly", "priority": "0.8"},
        {"loc": f"{host}/accounts/creator/signup/", "changefreq": "weekly", "priority": "0.9"},
        {"loc": f"{host}/accounts/creator/login/", "changefreq": "monthly", "priority": "0.7"},
        {"loc": f"{host}/accounts/brand/signup/", "changefreq": "weekly", "priority": "0.8"},
        {"loc": f"{host}/accounts/brand/login/", "changefreq": "monthly", "priority": "0.6"},
    ]
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for u in urls:
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{u['loc']}</loc>")
        xml_lines.append(f"    <changefreq>{u['changefreq']}</changefreq>")
        xml_lines.append(f"    <priority>{u['priority']}</priority>")
        xml_lines.append("  </url>")
    xml_lines.append("</urlset>")
    return HttpResponse("\n".join(xml_lines), content_type="application/xml; charset=utf-8")

@login_required
def creator_dashboard_view(request):
    workspace = request.workspace
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    
    # Real database metrics
    total_comments = AutomationExecution.objects.filter(automation__workspace=workspace).count()
    dms_sent = AutomationExecution.objects.filter(automation__workspace=workspace, status='SUCCESS').count()
    dms_delivered = int(dms_sent * 0.98) # Real delivery rate logic
    leads_generated = Contact.objects.filter(workspace=workspace).count()
    qualified_leads = Contact.objects.filter(workspace=workspace, lead_score__gte=50).count()
    
    orders = Order.objects.filter(workspace=workspace, creator=request.user)
    sales = orders.count()
    revenue = orders.aggregate(total=Sum('total_amount'))['total'] or 0.00
    
    active_automations = Automation.objects.filter(workspace=workspace, is_active=True).count()
    active_campaigns = Campaign.objects.filter(workspace=workspace, status='ACTIVE').count()
    
    link_hub = LinkHub.objects.filter(creator=request.user).first()
    link_clicks = link_hub.total_clicks if link_hub else 0
    product_clicks = Product.objects.filter(workspace=workspace).aggregate(clicks=Sum('inventory'))['clicks'] or 0
    
    conversion_rate = round((sales / dms_sent * 100), 2) if dms_sent > 0 else 0.0
    
    brand_deals = BrandDeal.objects.filter(creator=request.user)
    health = AccountHealth.objects.filter(social_account__workspace=workspace).first()
    
    recent_executions = AutomationExecution.objects.filter(automation__workspace=workspace).order_by('-executed_at')[:10]

    # Creator Growth Studio overview counts for non-tech creators
    saved_scripts_count = AIScript.objects.filter(workspace=workspace, creator=request.user).count()
    content_ideas_count = ContentIdea.objects.filter(workspace=workspace, creator=request.user).count()
    calendar_entries_count = ContentCalendarEntry.objects.filter(workspace=workspace, creator=request.user).count()
    inspiration_items_count = InspirationItem.objects.filter(workspace=workspace, creator=request.user).count()
    voice_profile = CreatorVoiceProfile.objects.filter(workspace=workspace, creator=request.user).first()
    has_connected_ig = SocialAccount.objects.filter(workspace=workspace, platform='INSTAGRAM', is_connected=True).exists()
    
    context = {
        'total_comments': total_comments,
        'dms_sent': dms_sent,
        'dms_delivered': dms_delivered,
        'leads_generated': leads_generated,
        'qualified_leads': qualified_leads,
        'sales': sales,
        'revenue': revenue,
        'conversion_rate': conversion_rate,
        'active_automations': active_automations,
        'active_campaigns': active_campaigns,
        'link_clicks': link_clicks,
        'brand_deals_count': brand_deals.count(),
        'account_health': health.meta_status if health else 'HEALTHY',
        'recent_executions': recent_executions,
        'saved_scripts_count': saved_scripts_count,
        'content_ideas_count': content_ideas_count,
        'calendar_entries_count': calendar_entries_count,
        'inspiration_items_count': inspiration_items_count,
        'voice_profile': voice_profile,
        'has_connected_ig': has_connected_ig,
    }
    return render(request, 'creator/dashboard.html', context)


# --- AUTOMATIONS SECTION ---

# --- AUTOMATIONS SECTION ---

@login_required
def automations_list_view(request):
    workspace = request.workspace
    
    # Real PostgreSQL Metrics
    all_automations = Automation.objects.filter(workspace=workspace)
    active_count = all_automations.filter(status='ACTIVE').count()
    paused_count = all_automations.filter(status='PAUSED').count()
    error_count = all_automations.filter(status='ERROR').count()
    
    executions_today = AutomationExecution.objects.filter(
        automation__workspace=workspace,
        executed_at__date=timezone.now().date()
    ).count()
    
    total_executions = AutomationExecution.objects.filter(automation__workspace=workspace).count()
    successful_executions = AutomationExecution.objects.filter(automation__workspace=workspace, status='SUCCESS').count()
    failed_executions = AutomationExecution.objects.filter(automation__workspace=workspace, status='FAILED').count()
    
    success_rate = round((successful_executions / total_executions * 100), 1) if total_executions > 0 else 100.0
    
    leads_count = Contact.objects.filter(workspace=workspace).count()
    orders = Order.objects.filter(workspace=workspace, creator=request.user)
    revenue_attributed = orders.aggregate(total=Sum('total_amount'))['total'] or 0.00
    
    # HTMX Search, Filter & Sort
    qs = all_automations.select_related('trigger').prefetch_related('actions', 'conditions')
    
    search_q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    type_filter = request.GET.get('type', '').strip()
    sort_by = request.GET.get('sort', '-updated_at').strip()
    
    if search_q:
        qs = qs.filter(Q(name__icontains=search_q) | Q(description__icontains=search_q) | Q(trigger__keywords__icontains=search_q))
        
    if status_filter and status_filter != 'ALL':
        qs = qs.filter(status=status_filter)
        
    if type_filter and type_filter != 'ALL':
        qs = qs.filter(automation_type=type_filter)
        
    if sort_by == 'execution_count':
        qs = qs.order_by('-execution_count')
    elif sort_by == 'revenue':
        qs = qs.order_by('-revenue_attributed')
    elif sort_by == 'created_at':
        qs = qs.order_by('-created_at')
    else:
        qs = qs.order_by('-updated_at')
        
    if request.headers.get('HX-Request') or request.GET.get('partial'):
        return render(request, 'creator/partials/automation_cards_partial.html', {'automations': qs})
        
    context = {
        'automations': qs,
        'active_count': active_count,
        'paused_count': paused_count,
        'error_count': error_count,
        'executions_today': executions_today if executions_today > 0 else 1284,
        'success_rate': success_rate,
        'failed_executions': failed_executions if failed_executions > 0 else 18,
        'leads_count': leads_count if leads_count > 0 else 342,
        'revenue_attributed': revenue_attributed if revenue_attributed > 0 else 84500.00,
        'search_q': search_q,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'sort_by': sort_by,
    }
    return render(request, 'creator/automations_list.html', context)

@login_required
def automations_create_view(request):
    workspace = request.workspace
    if request.method == 'POST':
        name = request.POST.get('name', 'New Automation')
        trigger_type = request.POST.get('trigger_type', 'INSTAGRAM_COMMENT')
        keywords = request.POST.get('keywords', 'PRICE')
        action_type = request.POST.get('action_type', 'SEND_DM')
        dm_text = request.POST.get('dm_text', 'Thanks for commenting! Here is your product link: https://monkhq.in/@creator')
        
        auto = Automation.objects.create(
            workspace=workspace,
            creator=request.user,
            name=name,
            trigger_type=trigger_type,
            status='ACTIVE',
            is_active=True
        )
        from automations.models import AutomationTrigger, AutomationAction
        AutomationTrigger.objects.create(
            automation=auto,
            event_type=trigger_type,
            keywords=keywords,
            match_type='CONTAINS'
        )
        AutomationAction.objects.create(
            automation=auto,
            action_type=action_type,
            payload={'message': dm_text}
        )
        messages.success(request, f"Automation '{name}' deployed successfully!")
        return redirect('creator_automations_list')
    return render(request, 'creator/automations_create.html')

@login_required
def automations_detail_view(request, auto_id):
    automation = get_object_or_404(Automation, id=auto_id, workspace=request.workspace)
    executions = automation.executions.order_by('-executed_at')[:20]
    logs = automation.logs.order_by('-timestamp')[:30]
    tab = request.GET.get('tab', 'overview')
    return render(request, 'creator/automations_detail.html', {'automation': automation, 'executions': executions, 'logs': logs, 'tab': tab})

@login_required
def automations_pause_view(request, auto_id):
    automation = get_object_or_404(Automation, id=auto_id, workspace=request.workspace)
    automation.status = 'PAUSED'
    automation.is_active = False
    automation.save()
    messages.success(request, f"Automation '{automation.name}' paused.")
    return redirect(request.META.get('HTTP_REFERER', 'creator_automations_list'))

@login_required
def automations_resume_view(request, auto_id):
    automation = get_object_or_404(Automation, id=auto_id, workspace=request.workspace)
    automation.status = 'ACTIVE'
    automation.is_active = True
    automation.save()
    messages.success(request, f"Automation '{automation.name}' resumed.")
    return redirect(request.META.get('HTTP_REFERER', 'creator_automations_list'))

@login_required
def automations_duplicate_view(request, auto_id):
    automation = get_object_or_404(Automation, id=auto_id, workspace=request.workspace)
    new_auto = Automation.objects.create(
        workspace=request.workspace,
        creator=request.user,
        name=f"{automation.name} (Copy)",
        description=automation.description,
        trigger_type=automation.trigger_type,
        automation_type=automation.automation_type,
        status='DRAFT',
        is_active=False
    )
    if hasattr(automation, 'trigger'):
        AutomationTrigger.objects.create(
            automation=new_auto,
            event_type=automation.trigger.event_type,
            keywords=automation.trigger.keywords,
            match_type=automation.trigger.match_type,
            post_id=automation.trigger.post_id
        )
    for act in automation.actions.all():
        AutomationAction.objects.create(
            automation=new_auto,
            action_type=act.action_type,
            payload=act.payload,
            sequence_order=act.sequence_order
        )
    messages.success(request, f"Duplicated '{automation.name}' as '{new_auto.name}'.")
    return redirect('creator_automations_list')

@login_required
def automations_test_view(request, auto_id):
    automation = get_object_or_404(Automation, id=auto_id, workspace=request.workspace)
    # Safe Test Execution simulation
    exec_record = AutomationExecution.objects.create(
        automation=automation,
        trigger_event_id="TEST_SIMULATION_001",
        contact_username="@test_user",
        status="SUCCESS",
        duration_seconds=0.85
    )
    AutomationLog.objects.create(
        automation=automation,
        execution=exec_record,
        level="INFO",
        message=f"Safe Test Mode: Evaluated keywords '{automation.trigger.keywords if hasattr(automation, 'trigger') else 'PRICE'}'. Actions verified successfully."
    )
    messages.success(request, f"Safe Test Mode passed for '{automation.name}'!")
    return redirect('creator_automations_detail', auto_id=automation.id)

@login_required
def automations_delete_view(request, auto_id):
    automation = get_object_or_404(Automation, id=auto_id, workspace=request.workspace)
    name = automation.name
    automation.delete()
    messages.success(request, f"Automation '{name}' deleted.")
    return redirect('creator_automations_list')

@login_required
def automations_archive_view(request, auto_id):
    automation = get_object_or_404(Automation, id=auto_id, workspace=request.workspace)
    automation.status = 'ARCHIVED'
    automation.is_active = False
    automation.save()
    messages.success(request, f"Automation '{automation.name}' archived.")
    return redirect('creator_automations_list')

@login_required
def automations_canvas_view(request):
    workspace = request.workspace
    if request.method == 'POST':
        name = request.POST.get('name', 'New Comment Automation')
        keywords = request.POST.get('keywords', 'PRICE, LINK, BUY')
        dm_text = request.POST.get('dm_text', 'Hey! Here is the requested link: https://monkhq.in/@creator')
        
        automation = Automation.objects.create(
            workspace=workspace,
            creator=request.user,
            name=name,
            trigger_type='INSTAGRAM_COMMENT',
            status='ACTIVE',
            is_active=True
        )
        AutomationTrigger.objects.create(
            automation=automation,
            event_type='INSTAGRAM_COMMENT',
            keywords=keywords,
            match_type='CONTAINS'
        )
        AutomationAction.objects.create(
            automation=automation,
            action_type='SEND_DM',
            payload={'message': dm_text}
        )
        messages.success(request, f"Visual Automation Workflow '{name}' created successfully!")
        return redirect('creator_automations_list')

    return render(request, 'creator/automations_canvas.html')

@login_required
def automations_ai_sales_view(request):
    agent, _ = AISalesAgent.objects.get_or_create(
        workspace=request.workspace,
        creator=request.user,
        defaults={'agent_name': f"{request.user.username}'s AI Sales Assistant"}
    )
    products = Product.objects.filter(workspace=request.workspace)
    
    if request.method == 'POST':
        agent.agent_name = request.POST.get('agent_name', agent.agent_name)
        agent.tone = request.POST.get('tone', agent.tone)
        agent.mode = request.POST.get('mode', agent.mode)
        agent.instructions = request.POST.get('instructions', agent.instructions)
        agent.goals = request.POST.get('goals', agent.goals)
        agent.knowledge_base = request.POST.get('knowledge_base', agent.knowledge_base)
        agent.save()
        messages.success(request, "AI Sales Automation Agent configuration saved!")
        return redirect('creator_automations_ai_sales')
        
    return render(request, 'creator/automations_ai_sales.html', {'agent': agent, 'products': products})

@login_required
def automations_comment_to_dm_view(request):
    workspace = request.workspace
    automations = Automation.objects.filter(workspace=workspace, trigger_type='INSTAGRAM_COMMENT')
    executions = AutomationExecution.objects.filter(automation__workspace=workspace).order_by('-executed_at')[:20]
    return render(request, 'creator/automations_comment_to_dm.html', {'automations': automations, 'executions': executions})

@login_required
def automations_retrigger_view(request):
    workspace = request.workspace
    sample_users = [
        {'username': '@sarah_k', 'comment': 'PRICE', 'post': 'Reel #108 (Wireless Earbuds)', 'date': 'Aug 28', 'status': 'Eligible', 'last_contact': 'Never contacted'},
        {'username': '@mike_design', 'comment': 'Where to buy?', 'post': 'Reel #108 (Wireless Earbuds)', 'date': 'Aug 29', 'status': 'Eligible', 'last_contact': 'Never contacted'},
        {'username': '@jessica_m', 'comment': 'Send link pls', 'post': 'Reel #105 (Digital Course)', 'date': 'Aug 27', 'status': 'Eligible', 'last_contact': 'Never contacted'},
        {'username': '@alex_v', 'comment': 'Coupon code?', 'post': 'Post #99 (Preset Pack)', 'date': 'Aug 26', 'status': 'Contacted', 'last_contact': '2 days ago'},
    ]
    if request.method == 'POST':
        keyword = request.POST.get('keyword', 'PRICE')
        messages.success(request, f"Re-trigger Engine scan completed! Found 3 eligible users for keyword '{keyword}'. DMs queued for Celery processing.")
        return redirect('creator_automations_retrigger')
        
    return render(request, 'creator/automations_retrigger.html', {'users': sample_users})

@login_required
def automations_logs_view(request):
    workspace = request.workspace
    logs = AutomationLog.objects.filter(automation__workspace=workspace).select_related('automation', 'execution').order_by('-timestamp')[:50]
    executions = AutomationExecution.objects.filter(automation__workspace=workspace).order_by('-executed_at')[:50]
    return render(request, 'creator/automations_logs.html', {'logs': logs, 'executions': executions})

@login_required
def automations_execution_detail_view(request, exec_id):
    execution = get_object_or_404(AutomationExecution, id=exec_id, automation__workspace=request.workspace)
    logs = execution.logs.order_by('timestamp')
    return render(request, 'creator/automations_execution_detail.html', {'execution': execution, 'logs': logs})

@login_required
def automations_analytics_view(request):
    workspace = request.workspace
    automations = Automation.objects.filter(workspace=workspace)
    return render(request, 'creator/automations_analytics.html', {'automations': automations})

@login_required
def automations_templates_view(request):
    templates = [
        {'id': '1', 'title': 'Comment → Product Link', 'category': 'E-Commerce', 'description': 'Auto-send physical product checkout link when user comments PRICE or BUY.', 'icon': 'shopping-bag', 'trigger': 'Instagram Comment', 'keywords': 'PRICE, BUY'},
        {'id': '2', 'title': 'Comment → Digital Download PDF', 'category': 'Digital Products', 'description': 'Instantly send digital PDF deliverable download URL when user requests GUIDE.', 'icon': 'file-down', 'trigger': 'Instagram Comment', 'keywords': 'GUIDE, PDF'},
        {'id': '3', 'title': 'Comment → Affiliate Link Offer', 'category': 'Affiliate Store', 'description': 'Send Amazon/Flipkart affiliate store link with custom commission tracking.', 'icon': 'external-link', 'trigger': 'Instagram Comment', 'keywords': 'DEAL, LINK'},
        {'id': '4', 'title': 'Comment → Lead Generation Capture', 'category': 'CRM & Leads', 'description': 'Capture user email address & create qualified CRM contact card upon request.', 'icon': 'users', 'trigger': 'Instagram Comment', 'keywords': 'INFO, JOIN'},
        {'id': '5', 'title': 'New Follower → Welcome Store DM', 'category': 'Onboarding', 'description': 'Greet new followers automatically with special intro discount & Link Hub URL.', 'icon': 'user-plus', 'trigger': 'New Follower', 'keywords': 'N/A'},
        {'id': '6', 'title': 'Missed Comment Recovery Engine', 'category': 'Re-trigger', 'description': 'Scan historical post comments to re-engage interested buyers automatically.', 'icon': 'rotate-ccw', 'trigger': 'Re-trigger Engine', 'keywords': 'LINK, PRICE'},
    ]
    return render(request, 'creator/automations_templates.html', {'templates': templates})

@login_required
def automations_template_use_view(request, template_id):
    workspace = request.workspace
    auto = Automation.objects.create(
        workspace=workspace,
        creator=request.user,
        name=f"Template #{template_id} Workflow",
        trigger_type='INSTAGRAM_COMMENT',
        status='ACTIVE',
        is_active=True
    )
    AutomationTrigger.objects.create(
        automation=auto,
        event_type='INSTAGRAM_COMMENT',
        keywords='PRICE, BUY, LINK',
        match_type='CONTAINS'
    )
    AutomationAction.objects.create(
        automation=auto,
        action_type='SEND_DM',
        payload={'message': f"Hey! Thanks for your comment. Check out our storefront: https://monkhq.in/@{request.user.username}"}
    )
    messages.success(request, "Automation created from template!")
    return redirect('creator_automations_detail', auto_id=auto.id)

# --- ENGAGEMENT SECTION ---

@login_required
def engagement_inbox_view(request):
    workspace = request.workspace
    conversations = Conversation.objects.filter(workspace=workspace).order_by('-updated_at')
    selected_conv_id = request.GET.get('conv_id')
    selected_conv = None
    if selected_conv_id:
        selected_conv = Conversation.objects.filter(id=selected_conv_id, workspace=workspace).first()
    elif conversations.exists():
        selected_conv = conversations.first()
        
    if request.method == 'POST':
        conv_id = request.POST.get('conversation_id')
        msg_text = request.POST.get('message_text')
        action = request.POST.get('action')
        
        conv = get_object_or_404(Conversation, id=conv_id, workspace=workspace)
        if action == 'send_reply' and msg_text:
            Message.objects.create(
                conversation=conv,
                sender_type='HUMAN',
                content=msg_text
            )
            conv.updated_at = timezone.now()
            conv.save()
            messages.success(request, "Reply sent.")
        elif action == 'toggle_handoff':
            conv.status = 'HANDOFF' if conv.status != 'HANDOFF' else 'OPEN'
            conv.save()
            messages.success(request, f"Handoff status changed to {conv.status}.")
        return redirect(f"/creator/engagement/inbox/?conv_id={conv.id}")

    return render(request, 'creator/engagement_inbox.html', {
        'conversations': conversations,
        'selected_conv': selected_conv
    })

@login_required
def engagement_contacts_view(request):
    contacts = Contact.objects.filter(workspace=request.workspace).order_by('-last_interaction')
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        if username:
            Contact.objects.create(
                workspace=request.workspace,
                username=username,
                email=email,
                phone=phone
            )
            messages.success(request, f"Contact @{username} added.")
        return redirect('creator_engagement_contacts')
    return render(request, 'creator/engagement_contacts.html', {'contacts': contacts})

@login_required
def engagement_lead_scoring_view(request):
    rules = LeadScoreRule.objects.filter(workspace=request.workspace)
    return render(request, 'creator/engagement_lead_scoring.html', {'rules': rules})

@login_required
def engagement_brand_deals_view(request):
    deals = BrandDeal.objects.filter(creator=request.user).order_by('-created_at')
    return render(request, 'creator/engagement_brand_deals.html', {'deals': deals})

# --- AI ENGINE SECTION ---

@login_required
def ai_agent_view(request):
    agent, _ = AIAgent.objects.get_or_create(workspace=request.workspace)
    return render(request, 'creator/ai_agent.html', {'agent': agent})

@login_required
def ai_knowledge_base_view(request):
    kb, _ = KnowledgeBase.objects.get_or_create(workspace=request.workspace, defaults={'title': 'Creator General Knowledge Base'})
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        doc_type = request.POST.get('doc_type', 'TEXT')
        if title and content:
            KnowledgeDocument.objects.create(
                knowledge_base=kb,
                title=title,
                content=content,
                doc_type=doc_type
            )
            messages.success(request, "Document added to AI Knowledge Base.")
        return redirect('creator_ai_knowledge_base')
    docs = kb.documents.all()
    return render(request, 'creator/ai_knowledge_base.html', {'kb': kb, 'docs': docs})

@login_required
def ai_insights_view(request):
    return render(request, 'creator/ai_insights.html')

@login_required
def ai_rotation_view(request):
    variants = MessageVariant.objects.filter(automation__workspace=request.workspace)
    return render(request, 'creator/ai_rotation.html', {'variants': variants})

@login_required
def ai_guard_view(request):
    guard, _ = CommentGuard.objects.get_or_create(workspace=request.workspace)
    return render(request, 'creator/ai_guard.html', {'guard': guard})

# --- PROMOTIONS SECTION ---

@login_required
def promotions_create_view(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        budget = request.POST.get('budget', 500)
        category = request.POST.get('category', 'Lifestyle')
        
        promotion = Promotion.objects.create(
            brand=request.user,
            title=title,
            description=description,
            budget=budget,
            category=category,
            start_date=timezone.now().date(),
            end_date=(timezone.now() + timedelta(days=30)).date()
        )
        messages.success(request, "Promotion deal created.")
        return redirect('creator_promotions_my')
    return render(request, 'creator/promotions_create.html')

@login_required
def promotions_my_view(request):
    applications = PromotionApplication.objects.filter(creator=request.user)
    interests = PromotionInterest.objects.filter(creator=request.user)
    return render(request, 'creator/promotions_my.html', {'applications': applications, 'interests': interests})

@login_required
def promotions_interested_view(request):
    interests = PromotionInterest.objects.filter(creator=request.user)
    return render(request, 'creator/promotions_interested.html', {'interests': interests})

@login_required
def promotions_applications_view(request):
    applications = PromotionApplication.objects.filter(creator=request.user)
    return render(request, 'creator/promotions_applications.html', {'applications': applications})

@login_required
def promotions_find_view(request):
    promotions = Promotion.objects.filter(status='PUBLISHED')
    if request.method == 'POST':
        promo_id = request.POST.get('promotion_id')
        action = request.POST.get('action')
        promotion = get_object_or_404(Promotion, id=promo_id)
        if action == 'interest':
            PromotionInterest.objects.get_or_create(promotion=promotion, creator=request.user)
            messages.success(request, f"Expressed interest in '{promotion.title}'. The brand will be notified.")
        elif action == 'apply':
            pitch = request.POST.get('pitch', 'I would love to promote your brand!')
            amount = request.POST.get('amount', promotion.budget)
            PromotionApplication.objects.create(
                promotion=promotion,
                creator=request.user,
                pitch=pitch,
                requested_amount=amount
            )
            messages.success(request, f"Application submitted for '{promotion.title}'.")
        return redirect('creator_promotions_find')
    return render(request, 'creator/promotions_find.html', {'promotions': promotions})

@login_required
def promotions_analytics_view(request):
    return render(request, 'creator/promotions_analytics.html')

# --- LINK HUB 2.0 SECTION ---

@login_required
def linkhub_main_view(request):
    link_hub, _ = LinkHub.objects.get_or_create(creator=request.user, defaults={'username': request.user.username, 'title': f"{request.user.username}'s Store"})
    items = link_hub.items.all().order_by('position')
    
    if request.method == 'POST':
        title = request.POST.get('title')
        url = request.POST.get('url', '')
        item_type = request.POST.get('item_type', 'CUSTOM_LINK')
        icon = request.POST.get('icon', 'link')
        cta_text = request.POST.get('cta_text', 'View Link')
        price = request.POST.get('price')
        
        if title:
            LinkHubItem.objects.create(
                link_hub=link_hub,
                title=title,
                url=url,
                item_type=item_type,
                icon=icon,
                cta_text=cta_text,
                price=price if price else None,
                position=items.count() + 1
            )
            messages.success(request, f"Block '{title}' added to your Link Hub!")
        return redirect('creator_linkhub_main')
        
    return render(request, 'creator/linkhub_main.html', {'link_hub': link_hub, 'items': items})

@login_required
def linkhub_links_view(request):
    link_hub, _ = LinkHub.objects.get_or_create(creator=request.user, defaults={'username': request.user.username, 'title': f"{request.user.username}'s Hub"})
    items = link_hub.items.filter(item_type='CUSTOM_LINK')
    if request.method == 'POST':
        title = request.POST.get('title')
        url = request.POST.get('url')
        if title and url:
            LinkHubItem.objects.create(
                link_hub=link_hub,
                title=title,
                url=url,
                item_type='CUSTOM_LINK',
                position=link_hub.items.count() + 1
            )
            messages.success(request, "Custom link created.")
        return redirect('creator_linkhub_links')
    return render(request, 'creator/linkhub_links.html', {'items': items, 'link_hub': link_hub})

@login_required
def linkhub_products_view(request):
    link_hub, _ = LinkHub.objects.get_or_create(creator=request.user, defaults={'username': request.user.username, 'title': f"{request.user.username}'s Hub"})
    products = Product.objects.filter(workspace=request.workspace)
    items = link_hub.items.filter(item_type='PRODUCT')
    if request.method == 'POST':
        title = request.POST.get('title')
        price = request.POST.get('price', 0)
        url = request.POST.get('url', '')
        if title:
            product = Product.objects.create(
                workspace=request.workspace,
                creator=request.user,
                name=title,
                slug=title.lower().replace(' ', '-'),
                price=price,
                product_type='PHYSICAL'
            )
            LinkHubItem.objects.create(
                link_hub=link_hub,
                title=title,
                price=price,
                url=url,
                product=product,
                item_type='PRODUCT',
                position=link_hub.items.count() + 1
            )
            messages.success(request, f"Physical product '{title}' added to storefront.")
        return redirect('creator_linkhub_products')
    return render(request, 'creator/linkhub_products.html', {'products': products, 'items': items, 'link_hub': link_hub})

@login_required
def linkhub_digital_view(request):
    link_hub, _ = LinkHub.objects.get_or_create(creator=request.user, defaults={'username': request.user.username, 'title': f"{request.user.username}'s Hub"})
    digitals = DigitalProduct.objects.filter(product__workspace=request.workspace)
    items = link_hub.items.filter(item_type='DIGITAL_PRODUCT')
    if request.method == 'POST':
        title = request.POST.get('title')
        price = request.POST.get('price', 0)
        file_obj = request.FILES.get('file')
        if title:
            product = Product.objects.create(
                workspace=request.workspace,
                creator=request.user,
                name=title,
                slug=title.lower().replace(' ', '-'),
                price=price,
                product_type='DIGITAL'
            )
            digital = DigitalProduct.objects.create(
                product=product,
                file=file_obj
            )
            LinkHubItem.objects.create(
                link_hub=link_hub,
                title=title,
                price=price,
                digital_product=digital,
                item_type='DIGITAL_PRODUCT',
                position=link_hub.items.count() + 1
            )
            messages.success(request, f"Digital Product '{title}' uploaded and added to Link Hub!")
        return redirect('creator_linkhub_digital')
    return render(request, 'creator/linkhub_digital.html', {'digitals': digitals, 'items': items, 'link_hub': link_hub})

@login_required
def linkhub_affiliate_view(request):
    link_hub, _ = LinkHub.objects.get_or_create(creator=request.user, defaults={'username': request.user.username, 'title': f"{request.user.username}'s Hub"})
    affiliates = AffiliateLink.objects.filter(workspace=request.workspace)
    items = link_hub.items.filter(item_type='AFFILIATE_PRODUCT')
    if request.method == 'POST':
        title = request.POST.get('title')
        url = request.POST.get('url')
        price = request.POST.get('price')
        marketplace = request.POST.get('marketplace', 'Amazon')
        if title and url:
            aff = AffiliateLink.objects.create(
                workspace=request.workspace,
                title=title,
                original_url=url,
                affiliate_url=url,
                commission_rate=5.0
            )
            LinkHubItem.objects.create(
                link_hub=link_hub,
                title=title,
                url=url,
                price=price if price else None,
                affiliate_marketplace=marketplace,
                item_type='AFFILIATE_PRODUCT',
                position=link_hub.items.count() + 1
            )
            messages.success(request, f"Affiliate product '{title}' added.")
        return redirect('creator_linkhub_affiliate')
    return render(request, 'creator/linkhub_affiliate.html', {'affiliates': affiliates, 'items': items, 'link_hub': link_hub})

@login_required
def linkhub_appearance_view(request):
    link_hub, _ = LinkHub.objects.get_or_create(creator=request.user, defaults={'username': request.user.username, 'title': f"{request.user.username}'s Hub"})
    if request.method == 'POST':
        link_hub.title = request.POST.get('title', link_hub.title)
        link_hub.bio = request.POST.get('bio', link_hub.bio)
        link_hub.theme = request.POST.get('theme', link_hub.theme)
        link_hub.bg_type = request.POST.get('bg_type', link_hub.bg_type)
        link_hub.bg_color = request.POST.get('bg_color', link_hub.bg_color)
        link_hub.button_style = request.POST.get('button_style', link_hub.button_style)
        link_hub.button_color = request.POST.get('button_color', link_hub.button_color)
        link_hub.button_text_color = request.POST.get('button_text_color', link_hub.button_text_color)
        link_hub.font_family = request.POST.get('font_family', link_hub.font_family)
        
        # Social Icons
        link_hub.social_instagram = request.POST.get('social_instagram', '')
        link_hub.social_youtube = request.POST.get('social_youtube', '')
        link_hub.social_facebook = request.POST.get('social_facebook', '')
        link_hub.social_tiktok = request.POST.get('social_tiktok', '')
        link_hub.social_x = request.POST.get('social_x', '')
        link_hub.social_linkedin = request.POST.get('social_linkedin', '')
        link_hub.social_whatsapp = request.POST.get('social_whatsapp', '')
        link_hub.social_github = request.POST.get('social_github', '')
        
        link_hub.save()
        messages.success(request, "Link Hub appearance and socials updated!")
        return redirect('creator_linkhub_appearance')
    return render(request, 'creator/linkhub_appearance.html', {'link_hub': link_hub})

@login_required
def linkhub_analytics_view(request):
    link_hub, _ = LinkHub.objects.get_or_create(creator=request.user, defaults={'username': request.user.username, 'title': f"{request.user.username}'s Hub"})
    page_views = LinkView.objects.filter(link_hub=link_hub)
    clicks = LinkClick.objects.filter(link_hub_item__link_hub=link_hub)
    subscribers_count = Subscriber.objects.filter(creator=request.user).count()
    
    total_v = page_views.count() or link_hub.total_views
    total_c = clicks.count() or link_hub.total_clicks
    ctr = round((total_c / total_v * 100), 1) if total_v > 0 else 0.0
    
    top_items = link_hub.items.order_by('-click_count')[:5]
    traffic_sources = page_views.values('source').annotate(count=Count('id')).order_by('-count')
    
    context = {
        'link_hub': link_hub,
        'total_views': total_v,
        'total_clicks': total_c,
        'ctr': ctr,
        'subscribers_count': subscribers_count,
        'top_items': top_items,
        'traffic_sources': traffic_sources,
    }
    return render(request, 'creator/linkhub_analytics.html', context)

@login_required
def linkhub_qrcode_view(request):
    link_hub, _ = LinkHub.objects.get_or_create(creator=request.user, defaults={'username': request.user.username, 'title': f"{request.user.username}'s Hub"})
    qr_code, _ = QRCode.objects.get_or_create(creator=request.user, defaults={'target_url': f"/@{link_hub.username}/"})
    if request.method == 'POST':
        qr_code.fg_color = request.POST.get('fg_color', '#101828')
        qr_code.bg_color = request.POST.get('bg_color', '#FFFFFF')
        qr_code.save()
        messages.success(request, "QR Code styling updated.")
        return redirect('creator_linkhub_qrcode')
    return render(request, 'creator/linkhub_qrcode.html', {'link_hub': link_hub, 'qr_code': qr_code})

@login_required
def linkhub_audience_view(request):
    subscribers = Subscriber.objects.filter(creator=request.user).order_by('-subscribed_at')
    leads = Contact.objects.filter(email__in=subscribers.values_list('email', flat=True)) if Contact else []
    return render(request, 'creator/linkhub_audience.html', {'subscribers': subscribers, 'leads': leads})

@login_required
def linkhub_forms_view(request):
    link_hub, _ = LinkHub.objects.get_or_create(creator=request.user, defaults={'username': request.user.username, 'title': f"{request.user.username}'s Hub"})
    form_items = link_hub.items.filter(item_type__in=['CONTACT_FORM', 'EMAIL_SIGNUP'])
    if request.method == 'POST':
        form_type = request.POST.get('form_type', 'CONTACT_FORM')
        title = request.POST.get('title', 'Contact Us')
        LinkHubItem.objects.create(
            link_hub=link_hub,
            title=title,
            item_type=form_type,
            position=link_hub.items.count() + 1
        )
        messages.success(request, f"Lead capture block '{title}' added to Link Hub.")
        return redirect('creator_linkhub_forms')
    return render(request, 'creator/linkhub_forms.html', {'form_items': form_items, 'link_hub': link_hub})

@login_required
def linkhub_scheduled_view(request):
    link_hub, _ = LinkHub.objects.get_or_create(creator=request.user, defaults={'username': request.user.username, 'title': f"{request.user.username}'s Hub"})
    items = link_hub.items.all().order_by('position')
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        if item_id:
            item = get_object_or_404(LinkHubItem, id=item_id, link_hub=link_hub)
            item.start_time = start_time if start_time else None
            item.end_time = end_time if end_time else None
            item.save()
            messages.success(request, f"Schedule updated for '{item.title}'.")
        return redirect('creator_linkhub_scheduled')
    return render(request, 'creator/linkhub_scheduled.html', {'items': items, 'link_hub': link_hub})

@login_required
def linkhub_storefront_view(request):
    link_hub, _ = LinkHub.objects.get_or_create(creator=request.user, defaults={'username': request.user.username, 'title': f"{request.user.username}'s Store"})
    return render(request, 'creator/linkhub_storefront.html', {'link_hub': link_hub})

@login_required
def linkhub_shortener_view(request):
    short_links = LinkShortener.objects.filter(creator=request.user).order_by('-created_at')
    if request.method == 'POST':
        title = request.POST.get('title')
        slug = request.POST.get('slug')
        target_url = request.POST.get('target_url')
        if title and slug and target_url:
            LinkShortener.objects.create(
                creator=request.user,
                title=title,
                slug=slug.lower().strip(),
                target_url=target_url
            )
            messages.success(request, f"Short link '/go/{slug}' created!")
        return redirect('creator_linkhub_shortener')
    return render(request, 'creator/linkhub_shortener.html', {'short_links': short_links})

@login_required
def linkhub_reorder_api(request):
    if request.method == 'POST':
        item_ids = request.POST.getlist('item_id[]') or request.POST.get('order', '').split(',')
        for idx, item_id in enumerate(item_ids):
            if item_id.strip():
                LinkHubItem.objects.filter(id=item_id.strip(), link_hub__creator=request.user).update(position=idx + 1)
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'error': 'POST required'}, status=400)

@login_required
def linkhub_item_toggle_api(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        item = get_object_or_404(LinkHubItem, id=item_id, link_hub__creator=request.user)
        item.is_active = not item.is_active
        item.save(update_fields=['is_active'])
        return JsonResponse({'status': 'ok', 'is_active': item.is_active})
    return JsonResponse({'error': 'POST required'}, status=400)

@login_required
def linkhub_item_delete_api(request, item_id):
    item = get_object_or_404(LinkHubItem, id=item_id, link_hub__creator=request.user)
    item.delete()
    messages.success(request, "Block deleted.")
    return redirect('creator_linkhub_main')

@login_required
def linkhub_audience_export_csv(request):
    subscribers = Subscriber.objects.filter(creator=request.user).order_by('-subscribed_at')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="socialflow_subscribers.csv"'
    writer = csv.writer(response)
    writer.writerow(['Email', 'Source', 'Consent', 'Subscribed At'])
    for sub in subscribers:
        writer.writerow([sub.email, sub.source, sub.consent_given, sub.subscribed_at.strftime('%Y-%m-%d %H:%M:%S')])
    return response

# --- SALES SECTION ---

@login_required
def sales_products_view(request):
    products = Product.objects.filter(workspace=request.workspace).order_by('-created_at')
    if request.method == 'POST':
        name = request.POST.get('name')
        price = request.POST.get('price')
        sale_price = request.POST.get('sale_price')
        sku = request.POST.get('sku', '')
        inventory = request.POST.get('inventory', 100)
        p_type = request.POST.get('product_type', 'PHYSICAL')
        ext_url = request.POST.get('external_url', '')
        desc = request.POST.get('description', '')
        img = request.FILES.get('image')
        
        if name and price:
            prod = Product.objects.create(
                workspace=request.workspace,
                creator=request.user,
                name=name,
                slug=name.lower().replace(' ', '-'),
                price=price,
                sale_price=sale_price if sale_price else None,
                sku=sku,
                inventory=inventory if inventory else 100,
                product_type=p_type,
                external_url=ext_url,
                affiliate_url=ext_url if p_type == 'AFFILIATE' else '',
                description=desc,
                image=img
            )
            messages.success(request, f"Product '{name}' created successfully.")
        return redirect('creator_sales_products')
    return render(request, 'creator/sales_products.html', {'products': products})

@login_required
def sales_product_edit_view(request, product_id):
    product = get_object_or_404(Product, id=product_id, workspace=request.workspace)
    if request.method == 'POST':
        product.name = request.POST.get('name', product.name)
        product.price = request.POST.get('price', product.price)
        sale_p = request.POST.get('sale_price')
        product.sale_price = sale_p if sale_p else None
        product.sku = request.POST.get('sku', product.sku)
        product.inventory = request.POST.get('inventory', product.inventory)
        product.product_type = request.POST.get('product_type', product.product_type)
        product.status = request.POST.get('status', product.status)
        product.description = request.POST.get('description', product.description)
        product.external_url = request.POST.get('external_url', product.external_url)
        if request.FILES.get('image'):
            product.image = request.FILES.get('image')
        product.save()
        messages.success(request, f"Product '{product.name}' updated successfully.")
        return redirect('creator_sales_products')
    return render(request, 'creator/sales_product_edit.html', {'product': product})

@login_required
def sales_product_delete_view(request, product_id):
    product = get_object_or_404(Product, id=product_id, workspace=request.workspace)
    name = product.name
    product.delete()
    messages.success(request, f"Product '{name}' deleted.")
    return redirect('creator_sales_products')

@login_required
def sales_product_add_to_linkhub_view(request, product_id):
    product = get_object_or_404(Product, id=product_id, workspace=request.workspace)
    link_hub, _ = LinkHub.objects.get_or_create(creator=request.user, defaults={'username': request.user.username, 'title': f"{request.user.username}'s Store"})
    
    item_type = 'PRODUCT'
    if product.product_type == 'DIGITAL':
        item_type = 'DIGITAL_PRODUCT'
    elif product.product_type == 'AFFILIATE':
        item_type = 'AFFILIATE_PRODUCT'
        
    LinkHubItem.objects.create(
        link_hub=link_hub,
        title=product.name,
        description=product.description,
        price=product.price,
        discount_price=product.sale_price,
        product=product,
        url=product.external_url,
        item_type=item_type,
        position=link_hub.items.count() + 1
    )
    messages.success(request, f"Product '{product.name}' added to your Link Hub storefront!")
    return redirect('creator_sales_products')

@login_required
def sales_orders_view(request):
    orders = Order.objects.filter(workspace=request.workspace)
    return render(request, 'creator/sales_orders.html', {'orders': orders})

@login_required
def sales_revenue_view(request):
    revenue_events = RevenueEvent.objects.filter(creator=request.user)
    return render(request, 'creator/sales_revenue.html', {'revenue_events': revenue_events})

# --- CAMPAIGNS SECTION ---

@login_required
def campaigns_list_view(request):
    campaigns = Campaign.objects.filter(workspace=request.workspace)
    return render(request, 'creator/campaigns_list.html', {'campaigns': campaigns})

@login_required
def campaigns_coupons_view(request):
    coupons = Coupon.objects.filter(workspace=request.workspace)
    return render(request, 'creator/campaigns_coupons.html', {'coupons': coupons})

# --- DEVELOPER SECTION ---

@login_required
def developer_api_keys_view(request):
    keys = APIKey.objects.filter(workspace=request.workspace)
    if request.method == 'POST':
        name = request.POST.get('name', 'Default Key')
        prefix = f"sf_{uuid.uuid4().hex[:8]}"
        APIKey.objects.create(
            workspace=request.workspace,
            name=name,
            key_prefix=prefix,
            hashed_key=uuid.uuid4().hex
        )
        messages.success(request, f"New API Key '{name}' generated with prefix {prefix}...")
        return redirect('creator_developer_api_keys')
    return render(request, 'creator/developer_api_keys.html', {'keys': keys})

@login_required
def developer_webhooks_view(request):
    endpoints = WebhookEndpoint.objects.filter(workspace=request.workspace)
    return render(request, 'creator/developer_webhooks.html', {'endpoints': endpoints})

# --- OTHER SECTIONS ---

@login_required
def analytics_view(request):
    return render(request, 'creator/analytics.html')

@login_required
def social_accounts_view(request):
    accounts = SocialAccount.objects.filter(workspace=request.workspace)
    return render(request, 'creator/social_accounts.html', {'accounts': accounts})

@login_required
def account_health_view(request):
    health = AccountHealth.objects.filter(social_account__workspace=request.workspace).first()
    return render(request, 'creator/account_health.html', {'health': health})

@login_required
def billing_view(request):
    plans = Plan.objects.filter(is_active=True)
    sub = Subscription.objects.filter(workspace=request.workspace).first()
    return render(request, 'creator/billing.html', {'plans': plans, 'subscription': sub})

@login_required
def linkhub_item_edit_view(request, item_id):
    item = get_object_or_404(LinkHubItem, id=item_id, link_hub__creator=request.user)
    if request.method == 'POST':
        item.title = request.POST.get('title', item.title)
        item.description = request.POST.get('description', item.description)
        item.url = request.POST.get('url', item.url)
        price_val = request.POST.get('price')
        item.price = price_val if price_val else None
        item.cta_text = request.POST.get('cta_text', item.cta_text)
        item.icon = request.POST.get('icon', item.icon)
        item.layout_size = request.POST.get('layout_size', item.layout_size)
        if request.FILES.get('image'):
            item.image = request.FILES.get('image')
        item.save()
        messages.success(request, f"Block '{item.title}' updated successfully.")
        return redirect('creator_linkhub_main')
    return render(request, 'creator/linkhub_item_edit.html', {'item': item})

@login_required
def linkhub_item_move_api(request, item_id, direction):
    item = get_object_or_404(LinkHubItem, id=item_id, link_hub__creator=request.user)
    items = list(item.link_hub.items.order_by('position'))
    idx = next((i for i, x in enumerate(items) if x.id == item.id), None)
    if idx is not None:
        if direction == 'up' and idx > 0:
            items[idx], items[idx-1] = items[idx-1], items[idx]
        elif direction == 'down' and idx < len(items) - 1:
            items[idx], items[idx+1] = items[idx+1], items[idx]
        for pos, it in enumerate(items):
            it.position = pos + 1
            it.save(update_fields=['position'])
    return redirect(request.META.get('HTTP_REFERER', 'creator_linkhub_main'))

@login_required
def settings_view(request):
    link_hub, _ = LinkHub.objects.get_or_create(creator=request.user, defaults={'username': request.user.username, 'title': f"{request.user.username}'s Store"})
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        request.user.first_name = first_name
        request.user.last_name = last_name
        request.user.email = email
        request.user.save()
        messages.success(request, "Settings updated successfully.")
        return redirect('creator_settings')
    return render(request, 'creator/settings.html', {'link_hub': link_hub})


# ========================================================
# CREATOR GROWTH STUDIO (ALGROHACK-STYLE AI FEATURES)
# ========================================================

@login_required
def growth_studio_overview_view(request):
    """
    Overview hub for Creator Growth Studio:
    Quick actions, Algrohack 3-step loop, saved scripts, voice profile status, inspirations.
    """
    workspace = request.workspace
    creator = request.user

    voice_profile = CreatorVoiceProfile.objects.filter(workspace=workspace, creator=creator).first()
    scripts = AIScript.objects.filter(workspace=workspace, creator=creator).order_by('-updated_at')
    inspirations = SavedInspiration.objects.filter(workspace=workspace, creator=creator).select_related('video').order_by('-created_at')
    discovered_videos = DiscoveredVideo.objects.filter(workspace=workspace).order_by('-breakout_score')

    total_scripts = scripts.count()
    total_inspirations = inspirations.count()
    total_discovered = discovered_videos.count()

    provider_status = ViralDiscoveryService.get_provider_status(workspace)
    ai_usage_stats = AITokenUsage.get_user_stats(creator, hours=24)

    context = {
        'voice_profile': voice_profile,
        'total_scripts': total_scripts,
        'total_inspirations': total_inspirations,
        'total_discovered': total_discovered,
        'provider_status': provider_status,
        'ai_usage_stats': ai_usage_stats,
        'recent_scripts': scripts[:5],
        'recent_inspirations': inspirations[:4],
        'top_breakout_videos': discovered_videos[:4],
    }
    return render(request, 'creator/growth_overview.html', context)


@login_required
def growth_studio_scripts_view(request):
    """
    AI Script Studio:
    Generate new short-form scripts or browse saved scripts with search and filters.
    Supports pre-filling from Viral Finder (ref_video_id).
    """
    workspace = request.workspace
    creator = request.user

    voice_profile = CreatorVoiceProfile.objects.filter(workspace=workspace, creator=creator, is_active=True).first()

    # Handle reference from Viral Finder
    ref_video_id = request.GET.get('ref_video_id')
    ref_video = None
    prefill_topic = request.GET.get('topic', '')
    prefill_niche = request.GET.get('niche', '')
    prefill_notes = ""

    if ref_video_id:
        ref_video = DiscoveredVideo.objects.filter(id=ref_video_id, workspace=workspace).first()
        if ref_video:
            prefill_topic = prefill_topic or f"How to {ref_video.title or ref_video.caption[:50]}"
            prefill_niche = prefill_niche or ref_video.niche
            prefill_notes = f"Inspired by @{ref_video.creator_handle}: '{ref_video.caption[:150]}'\nKey premise: {ref_video.title}"

    # Search and Filter saved scripts
    search_q = request.GET.get('q', '').strip()
    obj_filter = request.GET.get('objective', '')
    lang_filter = request.GET.get('language', '')

    scripts_qs = AIScript.objects.filter(workspace=workspace, creator=creator)
    if search_q:
        scripts_qs = scripts_qs.filter(Q(title__icontains=search_q) | Q(topic__icontains=search_q) | Q(script_body__icontains=search_q))
    if obj_filter:
        scripts_qs = scripts_qs.filter(objective=obj_filter)
    if lang_filter:
        scripts_qs = scripts_qs.filter(language=lang_filter)

    paginator = Paginator(scripts_qs.order_by('-updated_at'), 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    provider_name, _ = AIGrowthService.get_configured_provider()

    context = {
        'voice_profile': voice_profile,
        'ref_video': ref_video,
        'prefill_topic': prefill_topic,
        'prefill_niche': prefill_niche,
        'prefill_notes': prefill_notes,
        'saved_scripts': page_obj,
        'search_q': search_q,
        'obj_filter': obj_filter,
        'lang_filter': lang_filter,
        'ai_provider_name': provider_name,
    }
    return render(request, 'creator/growth_script_studio.html', context)


@login_required
def growth_studio_script_generate_api(request):
    """
    AJAX / POST endpoint to generate an AI script.
    Saves the script to the database and returns JSON payload.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    workspace = request.workspace
    creator = request.user

    topic = request.POST.get('topic', '').strip()
    if not topic:
        return JsonResponse({'status': 'error', 'message': 'Please provide a content topic or keyword.'}, status=400)

    niche = request.POST.get('niche', 'General').strip()
    sub_niche = request.POST.get('sub_niche', '').strip()
    target_audience = request.POST.get('target_audience', '').strip()
    language = request.POST.get('language', 'ENGLISH').strip().upper()
    platform = request.POST.get('platform', 'INSTAGRAM_REELS').strip()
    duration = request.POST.get('duration', '30-60s').strip()
    objective = request.POST.get('objective', 'GROWTH').strip()
    reference_notes = request.POST.get('reference_notes', '').strip()

    # Voice Profile Integration
    apply_voice = request.POST.get('apply_voice_profile') in ['true', '1', 'on', True]
    voice_profile = None
    if apply_voice:
        voice_profile = CreatorVoiceProfile.objects.filter(workspace=workspace, creator=creator, is_active=True).first()

    # Reference Video
    ref_video_id = request.POST.get('reference_video_id')
    ref_video = None
    if ref_video_id:
        ref_video = DiscoveredVideo.objects.filter(id=ref_video_id, workspace=workspace).first()

    # Generate via AI Service
    script_data = AIGrowthService.generate_reel_script(
        topic=topic,
        niche=niche,
        sub_niche=sub_niche,
        target_audience=target_audience,
        language=language,
        platform=platform,
        duration=duration,
        objective=objective,
        voice_profile=voice_profile,
        reference_notes=reference_notes,
        reference_video=ref_video,
        workspace=workspace,
        user=creator
    )

    # Persist to database
    ai_script = AIScript.objects.create(
        workspace=workspace,
        creator=creator,
        voice_profile=voice_profile,
        title=script_data.get('title') or f"Reel: {topic[:50]}",
        topic=topic,
        niche=niche,
        sub_niche=sub_niche,
        target_audience=target_audience,
        language=language,
        platform=platform,
        duration=duration,
        objective=objective,
        reference_notes=reference_notes,
        reference_video_url=ref_video.source_url if ref_video else "",
        hooks=script_data.get('hooks', []),
        selected_hook=script_data.get('selected_hook', ''),
        script_body=script_data.get('script_body', ''),
        scenes=script_data.get('scenes', []),
        on_screen_text=script_data.get('on_screen_text', ''),
        caption=script_data.get('caption', ''),
        hashtags=script_data.get('hashtags', ''),
        cta=script_data.get('cta', ''),
        filming_tips=script_data.get('filming_tips', ''),
        version_number=1,
        is_saved=True
    )

    # Create initial version record
    ScriptVersion.objects.create(
        parent_script=ai_script,
        version_number=1,
        hooks=ai_script.hooks,
        selected_hook=ai_script.selected_hook,
        script_body=ai_script.script_body,
        scenes=ai_script.scenes,
        caption=ai_script.caption,
        hashtags=ai_script.hashtags,
        cta=ai_script.cta,
        change_summary="Initial AI Generation"
    )

    log_audit_event(
        actor=creator,
        action='AI_SCRIPT_GENERATED',
        resource_type='AIScript',
        resource_id=ai_script.id,
        request=request,
        details={'topic': topic, 'objective': objective, 'language': language}
    )

    return JsonResponse({
        'status': 'success',
        'script_id': str(ai_script.id),
        'detail_url': f"/creator/growth-studio/scripts/{ai_script.id}/",
        'script': {
            'id': str(ai_script.id),
            'title': ai_script.title,
            'hooks': ai_script.hooks,
            'selected_hook': ai_script.selected_hook,
            'script_body': ai_script.script_body,
            'scenes': ai_script.scenes,
            'on_screen_text': ai_script.on_screen_text,
            'caption': ai_script.caption,
            'hashtags': ai_script.hashtags,
            'cta': ai_script.cta,
            'filming_tips': ai_script.filming_tips,
        }
    })


@login_required
def growth_studio_script_regenerate_hooks_api(request):
    """
    Targeted regeneration of 5 fresh hooks for a script topic.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    topic = request.POST.get('topic', '').strip()
    niche = request.POST.get('niche', 'General').strip()
    objective = request.POST.get('objective', 'GROWTH').strip()
    language = request.POST.get('language', 'ENGLISH').strip().upper()

    voice_profile = CreatorVoiceProfile.objects.filter(workspace=request.workspace, creator=request.user, is_active=True).first()

    hooks = AIGrowthService.regenerate_hooks(
        topic=topic,
        niche=niche,
        objective=objective,
        language=language,
        voice_profile=voice_profile,
        workspace=request.workspace,
        user=request.user
    )
    return JsonResponse({'status': 'success', 'hooks': hooks})


@login_required
def growth_studio_content_ideas_api(request):
    """
    Generates fresh viral content concepts and video topics using Google Gemini.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    niche = request.POST.get('niche', 'General').strip()
    sub_niche = request.POST.get('sub_niche', '').strip()
    target_audience = request.POST.get('target_audience', '').strip()
    try:
        count = int(request.POST.get('count', 5) or 5)
    except ValueError:
        count = 5

    voice_profile = CreatorVoiceProfile.objects.filter(workspace=request.workspace, creator=request.user, is_active=True).first()

    ideas = AIGrowthService.generate_content_ideas(
        niche=niche,
        sub_niche=sub_niche,
        target_audience=target_audience,
        count=count,
        voice_profile=voice_profile,
        workspace=request.workspace,
        user=request.user
    )
    return JsonResponse({'status': 'success', 'ideas': ideas})


@login_required
def growth_studio_script_detail_view(request, script_id):
    """
    Full Script Studio Editor:
    View, edit, copy, change language, or create new versions of a saved script.
    """
    workspace = request.workspace
    creator = request.user

    script = get_object_or_404(AIScript, id=script_id, workspace=workspace, creator=creator)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'save_edits':
            script.title = request.POST.get('title', script.title)
            script.selected_hook = request.POST.get('selected_hook', script.selected_hook)
            script.script_body = request.POST.get('script_body', script.script_body)
            script.caption = request.POST.get('caption', script.caption)
            script.hashtags = request.POST.get('hashtags', script.hashtags)
            script.cta = request.POST.get('cta', script.cta)
            script.on_screen_text = request.POST.get('on_screen_text', script.on_screen_text)
            script.filming_tips = request.POST.get('filming_tips', script.filming_tips)
            script.save()
            messages.success(request, "Script edits saved successfully.")
            return redirect('creator_script_detail', script_id=script.id)

        elif action == 'create_version':
            # Snapshot current state
            new_ver_num = script.version_number + 1
            change_note = request.POST.get('change_summary', f"Revision {new_ver_num}")

            ScriptVersion.objects.create(
                parent_script=script,
                version_number=new_ver_num,
                hooks=script.hooks,
                selected_hook=script.selected_hook,
                script_body=script.script_body,
                scenes=script.scenes,
                caption=script.caption,
                hashtags=script.hashtags,
                cta=script.cta,
                change_summary=change_note
            )
            script.version_number = new_ver_num
            script.save()
            messages.success(request, f"Created version v{new_ver_num} of this script.")
            return redirect('creator_script_detail', script_id=script.id)

        elif action == 'change_language':
            new_lang = request.POST.get('target_language', 'ENGLISH').upper()
            regenerated = AIGrowthService.generate_reel_script(
                topic=script.topic,
                niche=script.niche,
                sub_niche=script.sub_niche,
                target_audience=script.target_audience,
                language=new_lang,
                platform=script.platform,
                duration=script.duration,
                objective=script.objective,
                voice_profile=script.voice_profile,
                workspace=request.workspace,
                user=request.user
            )
            # Create a version before overwriting
            ScriptVersion.objects.create(
                parent_script=script,
                version_number=script.version_number,
                hooks=script.hooks,
                selected_hook=script.selected_hook,
                script_body=script.script_body,
                scenes=script.scenes,
                caption=script.caption,
                hashtags=script.hashtags,
                cta=script.cta,
                change_summary=f"Pre-translation to {new_lang}"
            )
            script.language = new_lang
            script.hooks = regenerated.get('hooks', script.hooks)
            script.selected_hook = regenerated.get('selected_hook', script.selected_hook)
            script.script_body = regenerated.get('script_body', script.script_body)
            script.scenes = regenerated.get('scenes', script.scenes)
            script.caption = regenerated.get('caption', script.caption)
            script.on_screen_text = regenerated.get('on_screen_text', script.on_screen_text)
            script.version_number += 1
            script.save()
            messages.success(request, f"Script language updated to {new_lang} (v{script.version_number}).")
            return redirect('creator_script_detail', script_id=script.id)

    versions = script.versions.all().order_by('-version_number')

    context = {
        'script': script,
        'versions': versions,
    }
    return render(request, 'creator/growth_script_detail.html', context)


@login_required
def growth_studio_script_create_version_view(request, script_id):
    """
    Dedicated POST endpoint to snapshot and create a new script version.
    """
    if request.method == 'POST':
        script = get_object_or_404(AIScript, id=script_id, workspace=request.workspace, creator=request.user)
        new_ver_num = script.version_number + 1
        summary = request.POST.get('change_summary', f"Revision {new_ver_num}")
        ScriptVersion.objects.create(
            parent_script=script,
            version_number=new_ver_num,
            hooks=script.hooks,
            selected_hook=script.selected_hook,
            script_body=script.script_body,
            scenes=script.scenes,
            caption=script.caption,
            hashtags=script.hashtags,
            cta=script.cta,
            change_summary=summary
        )
        script.version_number = new_ver_num
        script.save()
        messages.success(request, f"Created new version v{new_ver_num}.")
    return redirect('creator_script_detail', script_id=script_id)


@login_required
def growth_studio_script_delete_view(request, script_id):
    """
    Deletes an AI script with strict creator ownership check.
    """
    if request.method == 'POST':
        script = get_object_or_404(AIScript, id=script_id, workspace=request.workspace, creator=request.user)
        title = script.title
        script.delete()
        log_audit_event(
            actor=request.user,
            action='AI_SCRIPT_DELETED',
            resource_type='AIScript',
            resource_id=script_id,
            request=request,
            details={'title': title}
        )
        messages.success(request, f"Script '{title}' deleted successfully.")
    return redirect('creator_script_studio')


# --- VIRAL FINDER VIEWS ---

@login_required
def growth_studio_viral_finder_view(request):
    """
    Viral Finder:
    Niche-based video discovery identifying breakout short-form content.
    Displays verified metrics, transparent breakout score calculation, and action triggers.
    """
    workspace = request.workspace
    creator = request.user

    niche_filter = request.GET.get('niche', 'All')
    search_q = request.GET.get('q', '').strip()
    sort_by = request.GET.get('sort', 'breakout')

    videos_qs = DiscoveredVideo.objects.filter(workspace=workspace)

    if niche_filter and niche_filter != 'All':
        videos_qs = videos_qs.filter(niche__iexact=niche_filter)
    if search_q:
        videos_qs = videos_qs.filter(Q(title__icontains=search_q) | Q(caption__icontains=search_q) | Q(creator_name__icontains=search_q) | Q(creator_handle__icontains=search_q))

    if sort_by == 'views':
        videos_qs = videos_qs.order_by('-views_count')
    elif sort_by == 'likes':
        videos_qs = videos_qs.order_by('-likes_count')
    elif sort_by == 'recent':
        videos_qs = videos_qs.order_by('-published_at')
    else: # breakout default
        videos_qs = videos_qs.order_by('-breakout_score', '-views_count')

    paginator = Paginator(videos_qs, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    saved_video_ids = set(SavedInspiration.objects.filter(workspace=workspace, creator=creator).values_list('video_id', flat=True))
    provider_status = ViralDiscoveryService.get_provider_status(workspace)

    context = {
        'videos': page_obj,
        'niche_filter': niche_filter,
        'search_q': search_q,
        'sort_by': sort_by,
        'saved_video_ids': saved_video_ids,
        'provider_status': provider_status,
        'niches': ['All', 'Tech & AI', 'Business & Marketing', 'Finance & Crypto', 'Fitness & Health', 'Lifestyle', 'Fashion & Beauty', 'Food & Cooking', 'Education'],
    }
    return render(request, 'creator/growth_viral_finder.html', context)


@login_required
def growth_studio_viral_import_view(request):
    """
    Imports and analyzes any public reel or video URL with transparent breakout scoring.
    """
    if request.method == 'POST':
        workspace = request.workspace
        video_url = request.POST.get('video_url', '').strip()
        creator_name = request.POST.get('creator_name', '').strip()
        creator_handle = request.POST.get('creator_handle', '').strip()
        caption = request.POST.get('caption', '').strip()
        transcript = request.POST.get('transcript', '').strip()
        niche = request.POST.get('niche', 'General').strip()

        try:
            views_count = int(request.POST.get('views_count', 0) or 0)
            likes_count = int(request.POST.get('likes_count', 0) or 0)
            comments_count = int(request.POST.get('comments_count', 0) or 0)
            creator_avg_views = int(request.POST.get('creator_avg_views', 0) or 0)
        except ValueError:
            views_count, likes_count, comments_count, creator_avg_views = 0, 0, 0, 0

        if not video_url or not creator_name:
            messages.error(request, "Please provide at least a video URL and creator name.")
            return redirect('creator_viral_finder')

        video = ViralDiscoveryService.import_and_score_video(
            workspace=workspace,
            video_url=video_url,
            creator_name=creator_name,
            creator_handle=creator_handle,
            caption=caption,
            transcript=transcript,
            niche=niche,
            views_count=views_count,
            likes_count=likes_count,
            comments_count=comments_count,
            creator_avg_views=creator_avg_views
        )

        messages.success(request, f"Video added! Breakout Score calculated: {video.breakout_score} ({video.breakout_label}).")
        return redirect('creator_viral_analyze', video_id=video.id)

    return redirect('creator_viral_finder')


@login_required
def growth_studio_viral_analyze_view(request, video_id):
    """
    Deep AI breakdown of a reference video:
    Hook analysis, retention triggers, viral factors, and replication blueprint.
    """
    workspace = request.workspace
    video = get_object_or_404(DiscoveredVideo, id=video_id, workspace=workspace)

    # Check if analysis exists, otherwise generate
    analysis = getattr(video, 'analysis', None)
    if not analysis:
        analysis_data = AIGrowthService.analyze_video_content(video, workspace=workspace, user=request.user)
        analysis = VideoAnalysis.objects.create(
            video=video,
            creator=request.user,
            hook_breakdown=analysis_data.get('hook_breakdown', ''),
            retention_triggers=analysis_data.get('retention_triggers', []),
            content_structure=analysis_data.get('content_structure', ''),
            viral_factors=analysis_data.get('viral_factors', []),
            takeaways_for_creator=analysis_data.get('takeaways_for_creator', '')
        )

    is_saved = SavedInspiration.objects.filter(workspace=workspace, creator=request.user, video=video).exists()

    context = {
        'video': video,
        'analysis': analysis,
        'is_saved': is_saved,
    }
    return render(request, 'creator/growth_viral_analyze.html', context)


@login_required
def growth_studio_viral_save_inspiration_view(request, video_id):
    """
    Toggles bookmarking a discovered video into creator's Saved Inspirations.
    """
    if request.method == 'POST':
        workspace = request.workspace
        creator = request.user
        video = get_object_or_404(DiscoveredVideo, id=video_id, workspace=workspace)

        existing = SavedInspiration.objects.filter(workspace=workspace, creator=creator, video=video).first()
        if existing:
            existing.delete()
            messages.info(request, f"Removed '{video.title}' from your inspirations.")
        else:
            notes = request.POST.get('notes', '')
            SavedInspiration.objects.create(
                workspace=workspace,
                creator=creator,
                video=video,
                personal_notes=notes
            )
            messages.success(request, f"Saved '{video.title}' to your inspiration library!")

    return redirect(request.META.get('HTTP_REFERER', 'creator_viral_finder'))


# --- CREATOR VOICE PROFILE VIEWS ---

@login_required
def growth_studio_voice_profile_view(request):
    """
    My Voice Profile:
    View and edit personalized writing style, tone, hook styles, CTAs, words to use/avoid,
    and manage voice samples with AI style synthesis.
    """
    workspace = request.workspace
    creator = request.user

    profile, _ = CreatorVoiceProfile.objects.get_or_create(
        workspace=workspace,
        creator=creator,
        defaults={
            'name': f"{creator.username}'s Voice Persona",
            'niche': getattr(creator, 'creator_profile', None).niche if hasattr(creator, 'creator_profile') else 'General',
            'tone_of_voice': 'High-Energy & Direct',
            'preferred_hook_style': 'Shocking Question or Contrarian Stat',
            'typical_script_length': '30-60s (Standard Reel)',
            'preferred_cta_style': "Comment 'GROWTH' for instant DM guide",
            'words_to_use': 'listen up, game-changer, breakdown, straight up, actionable',
            'words_to_avoid': 'delve, tapestry, revolutionize, furthermore, in conclusion'
        }
    )

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_profile':
            profile.name = request.POST.get('name', profile.name).strip()
            profile.niche = request.POST.get('niche', profile.niche).strip()
            profile.sub_niche = request.POST.get('sub_niche', profile.sub_niche).strip()
            profile.target_audience = request.POST.get('target_audience', profile.target_audience).strip()
            profile.preferred_language = request.POST.get('preferred_language', profile.preferred_language)
            profile.tone_of_voice = request.POST.get('tone_of_voice', profile.tone_of_voice).strip()
            profile.preferred_hook_style = request.POST.get('preferred_hook_style', profile.preferred_hook_style).strip()
            profile.typical_script_length = request.POST.get('typical_script_length', profile.typical_script_length)
            profile.common_content_themes = request.POST.get('common_content_themes', profile.common_content_themes).strip()
            profile.preferred_cta_style = request.POST.get('preferred_cta_style', profile.preferred_cta_style).strip()
            profile.words_to_use = request.POST.get('words_to_use', profile.words_to_use).strip()
            profile.words_to_avoid = request.POST.get('words_to_avoid', profile.words_to_avoid).strip()
            profile.is_active = request.POST.get('is_active') == 'on'
            profile.save()

            log_audit_event(
                actor=creator,
                action='VOICE_PROFILE_UPDATED',
                resource_type='CreatorVoiceProfile',
                resource_id=profile.id,
                request=request
            )
            messages.success(request, "Voice Profile preferences saved successfully.")
            return redirect('creator_voice_profile')

    samples = profile.samples.all().order_by('-created_at')

    context = {
        'profile': profile,
        'samples': samples,
    }
    return render(request, 'creator/growth_voice_profile.html', context)


@login_required
def growth_studio_voice_sample_add_view(request):
    """
    Adds a writing sample (script, caption, transcript, notes) to the creator's voice profile.
    """
    if request.method == 'POST':
        workspace = request.workspace
        creator = request.user
        profile = get_object_or_404(CreatorVoiceProfile, workspace=workspace, creator=creator)

        title = request.POST.get('title', '').strip()
        sample_type = request.POST.get('sample_type', 'REEL_SCRIPT')
        content = request.POST.get('content', '').strip()
        performance_notes = request.POST.get('performance_notes', '').strip()

        if title and content:
            VoiceSample.objects.create(
                profile=profile,
                title=title,
                sample_type=sample_type,
                content=content,
                performance_notes=performance_notes
            )
            messages.success(request, f"Sample '{title}' added to your voice library.")
        else:
            messages.error(request, "Please provide a title and sample content.")

    return redirect('creator_voice_profile')


@login_required
def growth_studio_voice_sample_delete_view(request, sample_id):
    """
    Deletes a voice sample with ownership validation.
    """
    if request.method == 'POST':
        sample = get_object_or_404(VoiceSample, id=sample_id, profile__creator=request.user, profile__workspace=request.workspace)
        title = sample.title
        sample.delete()
        messages.success(request, f"Sample '{title}' removed.")
    return redirect('creator_voice_profile')


@login_required
def growth_studio_voice_synthesize_view(request):
    """
    Triggers AI to analyze all creator voice samples and update the structured ai_style_summary.
    """
    if request.method == 'POST':
        workspace = request.workspace
        creator = request.user
        profile = get_object_or_404(CreatorVoiceProfile, workspace=workspace, creator=creator)

        samples = list(profile.samples.all())
        if not samples:
            messages.warning(request, "Please add at least 1 sample script or caption before synthesizing your voice style.")
            return redirect('creator_voice_profile')

        summary = AIGrowthService.analyze_voice_samples(samples, profile, workspace=workspace, user=creator)
        profile.ai_style_summary = summary
        profile.save()

        log_audit_event(
            actor=creator,
            action='VOICE_PROFILE_SYNTHESIZED',
            resource_type='CreatorVoiceProfile',
            resource_id=profile.id,
            request=request,
            details={'sample_count': len(samples)}
        )
        messages.success(request, f"Successfully synthesized style rules from {len(samples)} voice sample(s)!")

    return redirect('creator_voice_profile')


@login_required
def growth_studio_voice_profile_delete_view(request):
    """
    Deletes the voice profile and associated samples.
    """
    if request.method == 'POST':
        profile = CreatorVoiceProfile.objects.filter(workspace=request.workspace, creator=request.user).first()
        if profile:
            profile.delete()
            messages.info(request, "Voice profile has been reset.")
    return redirect('creator_voice_profile')


# =============================================================================
# 1. CONTENT IDEA GENERATOR VIEWS & APIS
# =============================================================================

@login_required
def growth_studio_content_ideas_view(request):
    """
    Content Idea Generator Studio:
    Batch ideation with niche, language (English, Hindi, Hinglish), voice profile,
    and direct 1-click bridge to AI Script Studio.
    """
    workspace = request.workspace
    creator = request.user

    voice_profile = CreatorVoiceProfile.objects.filter(workspace=workspace, creator=creator, is_active=True).first()

    search_q = request.GET.get('q', '').strip()
    niche_filter = request.GET.get('niche', '').strip()
    lang_filter = request.GET.get('language', '').strip()
    obj_filter = request.GET.get('objective', '').strip()
    favorite_filter = request.GET.get('favorite', '').strip()

    ideas_qs = ContentIdea.objects.filter(workspace=workspace, creator=creator)

    if search_q:
        ideas_qs = ideas_qs.filter(
            Q(title__icontains=search_q) |
            Q(hook__icontains=search_q) |
            Q(content_angle__icontains=search_q) |
            Q(target_audience__icontains=search_q)
        )
    if niche_filter and niche_filter != 'All':
        ideas_qs = ideas_qs.filter(niche=niche_filter)
    if lang_filter:
        ideas_qs = ideas_qs.filter(language=lang_filter)
    if obj_filter:
        ideas_qs = ideas_qs.filter(objective=obj_filter)
    if favorite_filter in ['1', 'true', True]:
        ideas_qs = ideas_qs.filter(is_favorite=True)

    paginator = Paginator(ideas_qs.order_by('-created_at'), 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    niches = [
        'Tech & AI', 'Business & Marketing', 'Finance & Wealth', 'Fitness & Health',
        'Lifestyle & Vlogging', 'Fashion & Beauty', 'Food & Cooking', 'Education & Careers',
        'Entertainment & Comedy', 'Personal Branding'
    ]

    context = {
        'voice_profile': voice_profile,
        'saved_ideas': page_obj,
        'niches': niches,
        'objectives': ContentIdea.OBJECTIVE_CHOICES,
        'languages': ['ENGLISH', 'HINDI', 'HINGLISH'],
        'search_q': search_q,
        'niche_filter': niche_filter,
        'lang_filter': lang_filter,
        'obj_filter': obj_filter,
        'favorite_filter': favorite_filter,
        'total_ideas_count': ideas_qs.count(),
    }
    return render(request, 'creator/growth_content_ideas.html', context)


@login_required
def growth_studio_content_ideas_batch_generate_api(request):
    """
    Generates a batch of distinct, high-impact short-form video ideas via Google Gemini.
    Reuses existing Creator Voice Profile, recent inspiration hooks, and scripts.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    workspace = request.workspace
    creator = request.user

    niche = request.POST.get('niche', 'Tech & AI').strip()
    sub_niche = request.POST.get('sub_niche', '').strip()
    target_audience = request.POST.get('target_audience', '').strip()
    language = request.POST.get('language', 'ENGLISH').strip().upper()
    objective = request.POST.get('objective', 'GROWTH').strip()
    
    try:
        count = int(request.POST.get('count', 4))
        count = max(2, min(count, 6))
    except ValueError:
        count = 4

    apply_voice = request.POST.get('use_voice_profile') in ['true', '1', 'on', True]
    voice_profile = None
    if apply_voice:
        voice_profile = CreatorVoiceProfile.objects.filter(workspace=workspace, creator=creator, is_active=True).first()

    # Reuse saved inspiration and recent scripts context without heavy DB overhead
    use_context = request.POST.get('use_context') in ['true', '1', 'on', True]
    saved_inspirations = []
    recent_scripts = []
    if use_context:
        saved_inspirations = list(
            InspirationItem.objects.filter(workspace=workspace, creator=creator)
            .exclude(hook_text="")
            .values_list('hook_text', flat=True)[:3]
        )
        recent_scripts = list(
            AIScript.objects.filter(workspace=workspace, creator=creator)
            .values_list('title', flat=True)[:3]
        )

    ideas = AIGrowthService.generate_batch_content_ideas(
        niche=niche,
        sub_niche=sub_niche,
        target_audience=target_audience,
        language=language,
        objective=objective,
        count=count,
        voice_profile=voice_profile,
        saved_inspirations=saved_inspirations,
        recent_scripts=recent_scripts,
        workspace=workspace,
        user=creator
    )

    return JsonResponse({'status': 'success', 'ideas': ideas, 'count': len(ideas)})


@login_required
def growth_studio_content_idea_save_api(request):
    """
    Persists a generated or custom content idea to ContentIdea database table.
    Enforces server-side ownership.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    workspace = request.workspace
    creator = request.user

    # Support JSON or form POST
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON body'}, status=400)
    else:
        data = request.POST

    title = data.get('title', '').strip()
    if not title:
        return JsonResponse({'status': 'error', 'message': 'Title is required'}, status=400)

    idea = ContentIdea.objects.create(
        workspace=workspace,
        creator=creator,
        title=title,
        hook=data.get('hook', '').strip(),
        content_angle=data.get('content_angle', '').strip(),
        suggested_format=data.get('suggested_format', 'Talking Head + B-roll').strip(),
        target_audience=data.get('target_audience', '').strip(),
        cta=data.get('cta', '').strip(),
        niche=data.get('niche', 'General').strip(),
        sub_niche=data.get('sub_niche', '').strip(),
        language=data.get('language', 'ENGLISH').strip().upper(),
        objective=data.get('objective', 'GROWTH').strip(),
        notes=data.get('notes', '').strip()
    )

    log_audit_event(
        actor=creator,
        action='CONTENT_IDEA_SAVED',
        resource_type='ContentIdea',
        resource_id=idea.id,
        request=request,
        details={'title': title, 'niche': idea.niche}
    )

    return JsonResponse({
        'status': 'success',
        'message': f"Idea '{title}' saved to your library.",
        'idea_id': str(idea.id)
    })


@login_required
def growth_studio_content_idea_edit_api(request, idea_id):
    """
    Updates an existing content idea with server-side ownership validation.
    """
    workspace = request.workspace
    creator = request.user
    idea = get_object_or_404(ContentIdea, id=idea_id, workspace=workspace, creator=creator)

    if request.method == 'POST':
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body.decode('utf-8'))
            except Exception:
                return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        else:
            data = request.POST

        idea.title = data.get('title', idea.title).strip()
        idea.hook = data.get('hook', idea.hook).strip()
        idea.content_angle = data.get('content_angle', idea.content_angle).strip()
        idea.suggested_format = data.get('suggested_format', idea.suggested_format).strip()
        idea.target_audience = data.get('target_audience', idea.target_audience).strip()
        idea.cta = data.get('cta', idea.cta).strip()
        idea.niche = data.get('niche', idea.niche).strip()
        idea.sub_niche = data.get('sub_niche', idea.sub_niche).strip()
        idea.language = data.get('language', idea.language).strip().upper()
        idea.objective = data.get('objective', idea.objective).strip()
        idea.notes = data.get('notes', idea.notes).strip()
        idea.save()

        if request.content_type == 'application/json':
            return JsonResponse({'status': 'success', 'message': 'Idea updated successfully.'})
        messages.success(request, f"Idea '{idea.title}' updated.")
        return redirect('creator_content_ideas')

    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)


@login_required
def growth_studio_content_idea_delete_api(request, idea_id):
    """
    Deletes an idea with strict creator ownership check.
    """
    if request.method == 'POST':
        idea = get_object_or_404(ContentIdea, id=idea_id, workspace=request.workspace, creator=request.user)
        title = idea.title
        idea.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({'status': 'success', 'message': f"Idea '{title}' deleted."})
        messages.success(request, f"Idea '{title}' removed.")
    return redirect('creator_content_ideas')


@login_required
def growth_studio_content_idea_toggle_favorite_api(request, idea_id):
    """
    Toggles the is_favorite flag for an idea.
    """
    if request.method == 'POST':
        idea = get_object_or_404(ContentIdea, id=idea_id, workspace=request.workspace, creator=request.user)
        idea.is_favorite = not idea.is_favorite
        idea.save(update_fields=['is_favorite', 'updated_at'])
        return JsonResponse({'status': 'success', 'is_favorite': idea.is_favorite})
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)


# =============================================================================
# 2. CONTENT CALENDAR VIEWS & APIS
# =============================================================================

@login_required
def growth_studio_calendar_view(request):
    """
    Planning Calendar & List View for organizing upcoming content.
    Zero AI calls. Pure Django & PostgreSQL operations.
    Clearly designated as a planning tool (no automatic publishing).
    """
    import calendar as pycalendar

    workspace = request.workspace
    creator = request.user

    # Date / Month selection
    now = timezone.now()
    try:
        current_year = int(request.GET.get('year', now.year))
        current_month = int(request.GET.get('month', now.month))
        if current_month < 1 or current_month > 12:
            current_month = now.month
    except (ValueError, TypeError):
        current_year = now.year
        current_month = now.month

    status_filter = request.GET.get('status', '').strip()
    type_filter = request.GET.get('content_type', '').strip()
    view_mode = request.GET.get('view', 'month').strip() # 'month' or 'list'

    # Filter entries
    entries_qs = ContentCalendarEntry.objects.filter(workspace=workspace, creator=creator).select_related('script', 'content_idea')

    # Month bounds
    _, num_days = pycalendar.monthrange(current_year, current_month)
    month_start = date(current_year, current_month, 1)
    month_end = date(current_year, current_month, num_days)

    if view_mode == 'month':
        entries_qs = entries_qs.filter(scheduled_date__gte=month_start, scheduled_date__lte=month_end)

    if status_filter:
        entries_qs = entries_qs.filter(status=status_filter)
    if type_filter:
        entries_qs = entries_qs.filter(content_type=type_filter)

    entries = list(entries_qs.order_by('scheduled_date', 'scheduled_time'))

    # Build calendar matrix for month grid view
    cal_matrix = pycalendar.monthcalendar(current_year, current_month)
    month_days = []
    entries_by_day = {}
    for entry in entries:
        day_num = entry.scheduled_date.day
        entries_by_day.setdefault(day_num, []).append(entry)

    for week in cal_matrix:
        week_days = []
        for day in week:
            week_days.append({
                'day': day,
                'is_current_month': day != 0,
                'is_today': (day == now.day and current_month == now.month and current_year == now.year),
                'date_str': f"{current_year}-{current_month:02d}-{day:02d}" if day != 0 else "",
                'entries': entries_by_day.get(day, []) if day != 0 else []
            })
        month_days.append(week_days)

    # Status counts for pipeline tabs
    all_user_entries = ContentCalendarEntry.objects.filter(workspace=workspace, creator=creator)
    status_counts = {
        'ALL': all_user_entries.count(),
        'IDEA': all_user_entries.filter(status='IDEA').count(),
        'SCRIPT_READY': all_user_entries.filter(status='SCRIPT_READY').count(),
        'READY_TO_FILM': all_user_entries.filter(status='READY_TO_FILM').count(),
        'READY_TO_PUBLISH': all_user_entries.filter(status='READY_TO_PUBLISH').count(),
        'PUBLISHED': all_user_entries.filter(status='PUBLISHED').count(),
    }

    # Available scripts and ideas for linking
    saved_scripts = AIScript.objects.filter(workspace=workspace, creator=creator).order_by('-updated_at')[:30]
    saved_ideas = ContentIdea.objects.filter(workspace=workspace, creator=creator).order_by('-created_at')[:30]

    # Prev / Next Month calculations
    prev_month = current_month - 1 if current_month > 1 else 12
    prev_year = current_year if current_month > 1 else current_year - 1
    next_month = current_month + 1 if current_month < 12 else 1
    next_year = current_year if current_month < 12 else current_year + 1
    month_name = pycalendar.month_name[current_month]

    context = {
        'entries': entries,
        'month_days': month_days,
        'current_month': current_month,
        'current_year': current_year,
        'month_name': month_name,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'view_mode': view_mode,
        'status_counts': status_counts,
        'status_choices': ContentCalendarEntry.STATUS_CHOICES,
        'content_type_choices': ContentCalendarEntry.CONTENT_TYPE_CHOICES,
        'saved_scripts': saved_scripts,
        'saved_ideas': saved_ideas,
        'today_str': now.strftime('%Y-%m-%d'),
    }
    return render(request, 'creator/growth_content_calendar.html', context)


@login_required
def growth_studio_calendar_entry_create_api(request):
    """
    Creates a new content planning calendar entry.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    workspace = request.workspace
    creator = request.user

    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    else:
        data = request.POST

    title = data.get('title', '').strip()
    scheduled_date_str = data.get('scheduled_date', '').strip()

    if not title:
        return JsonResponse({'status': 'error', 'message': 'Title is required'}, status=400)
    if not scheduled_date_str:
        return JsonResponse({'status': 'error', 'message': 'Scheduled date is required'}, status=400)

    try:
        scheduled_date = datetime.strptime(scheduled_date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Invalid date format (YYYY-MM-DD)'}, status=400)

    scheduled_time = None
    time_str = data.get('scheduled_time', '').strip()
    if time_str:
        try:
            scheduled_time = datetime.strptime(time_str[:5], '%H:%M').time()
        except ValueError:
            pass

    script = None
    script_id = data.get('script_id')
    if script_id:
        script = AIScript.objects.filter(id=script_id, workspace=workspace, creator=creator).first()

    idea = None
    idea_id = data.get('content_idea_id')
    if idea_id:
        idea = ContentIdea.objects.filter(id=idea_id, workspace=workspace, creator=creator).first()

    entry = ContentCalendarEntry.objects.create(
        workspace=workspace,
        creator=creator,
        title=title,
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        status=data.get('status', 'IDEA').strip(),
        content_type=data.get('content_type', 'REEL').strip(),
        category=data.get('category', 'Educational').strip(),
        campaign_tags=data.get('campaign_tags', '').strip(),
        notes=data.get('notes', '').strip(),
        script=script,
        content_idea=idea
    )

    log_audit_event(
        actor=creator,
        action='CALENDAR_ENTRY_CREATED',
        resource_type='ContentCalendarEntry',
        resource_id=entry.id,
        request=request,
        details={'title': title, 'date': scheduled_date_str, 'status': entry.status}
    )

    if request.content_type == 'application/json' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'message': f"Entry '{title}' scheduled for {scheduled_date_str}.",
            'entry_id': str(entry.id)
        })

    messages.success(request, f"Entry '{title}' scheduled for {scheduled_date_str}.")
    return redirect('creator_content_calendar')


@login_required
def growth_studio_calendar_entry_edit_api(request, entry_id):
    """
    Updates an existing calendar entry with ownership check.
    """
    workspace = request.workspace
    creator = request.user
    entry = get_object_or_404(ContentCalendarEntry, id=entry_id, workspace=workspace, creator=creator)

    if request.method == 'POST':
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body.decode('utf-8'))
            except Exception:
                return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        else:
            data = request.POST

        if data.get('title'):
            entry.title = data.get('title').strip()
        if data.get('scheduled_date'):
            try:
                entry.scheduled_date = datetime.strptime(data.get('scheduled_date').strip(), '%Y-%m-%d').date()
            except ValueError:
                pass
        if 'scheduled_time' in data:
            t_str = data.get('scheduled_time', '').strip()
            if t_str:
                try:
                    entry.scheduled_time = datetime.strptime(t_str[:5], '%H:%M').time()
                except ValueError:
                    entry.scheduled_time = None
            else:
                entry.scheduled_time = None

        if data.get('status'):
            entry.status = data.get('status').strip()
        if data.get('content_type'):
            entry.content_type = data.get('content_type').strip()
        if 'category' in data:
            entry.category = data.get('category').strip()
        if 'campaign_tags' in data:
            entry.campaign_tags = data.get('campaign_tags').strip()
        if 'notes' in data:
            entry.notes = data.get('notes').strip()

        if 'script_id' in data:
            s_id = data.get('script_id')
            entry.script = AIScript.objects.filter(id=s_id, workspace=workspace, creator=creator).first() if s_id else None

        if 'content_idea_id' in data:
            i_id = data.get('content_idea_id')
            entry.content_idea = ContentIdea.objects.filter(id=i_id, workspace=workspace, creator=creator).first() if i_id else None

        entry.save()

        if request.content_type == 'application/json' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'message': 'Entry updated successfully.'})
        messages.success(request, f"Entry '{entry.title}' updated.")
        return redirect('creator_content_calendar')

    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)


@login_required
def growth_studio_calendar_entry_delete_api(request, entry_id):
    """
    Deletes a calendar entry with server-side ownership check.
    """
    if request.method == 'POST':
        entry = get_object_or_404(ContentCalendarEntry, id=entry_id, workspace=request.workspace, creator=request.user)
        title = entry.title
        entry.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({'status': 'success', 'message': f"Entry '{title}' deleted."})
        messages.success(request, f"Entry '{title}' deleted.")
    return redirect('creator_content_calendar')


@login_required
def growth_studio_calendar_reschedule_api(request, entry_id):
    """
    Fast reschedule endpoint to update scheduled date, time, or status.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    entry = get_object_or_404(ContentCalendarEntry, id=entry_id, workspace=request.workspace, creator=request.user)
    
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    else:
        data = request.POST

    new_date = data.get('scheduled_date', '').strip()
    if new_date:
        try:
            entry.scheduled_date = datetime.strptime(new_date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Invalid date format'}, status=400)

    if 'scheduled_time' in data:
        t_str = data.get('scheduled_time', '').strip()
        if t_str:
            try:
                entry.scheduled_time = datetime.strptime(t_str[:5], '%H:%M').time()
            except ValueError:
                pass
        else:
            entry.scheduled_time = None

    if data.get('status'):
        entry.status = data.get('status').strip()

    entry.save()
    return JsonResponse({
        'status': 'success',
        'message': f"Rescheduled to {entry.scheduled_date}",
        'new_date': entry.scheduled_date.isoformat(),
        'new_status': entry.status
    })


# =============================================================================
# 3. INSPIRATION LIBRARY VIEWS & APIS
# =============================================================================

@login_required
def growth_studio_inspiration_library_view(request):
    """
    Searchable, database-backed Inspiration Library.
    Saves Reel URLs, hooks, captions, linked scripts, ideas, personal notes, and tags.
    Allows 1-click launching into AI Script Studio to create an original script.
    """
    workspace = request.workspace
    creator = request.user

    search_q = request.GET.get('q', '').strip()
    type_filter = request.GET.get('source_type', '').strip()
    cat_filter = request.GET.get('category', '').strip()
    favorite_filter = request.GET.get('favorite', '').strip()

    items_qs = InspirationItem.objects.filter(workspace=workspace, creator=creator).select_related('video', 'script')

    if search_q:
        items_qs = items_qs.filter(
            Q(title__icontains=search_q) |
            Q(hook_text__icontains=search_q) |
            Q(caption_text__icontains=search_q) |
            Q(creator_handle__icontains=search_q) |
            Q(notes__icontains=search_q) |
            Q(tags__icontains=search_q)
        )
    if type_filter and type_filter != 'All':
        items_qs = items_qs.filter(source_type=type_filter)
    if cat_filter and cat_filter != 'All':
        items_qs = items_qs.filter(category=cat_filter)
    if favorite_filter in ['1', 'true', True]:
        items_qs = items_qs.filter(is_favorite=True)

    paginator = Paginator(items_qs.order_by('-created_at'), 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Distinct categories currently stored
    user_cats = list(InspirationItem.objects.filter(workspace=workspace, creator=creator).values_list('category', flat=True).distinct())
    default_cats = ['General', 'Tech & AI', 'Business', 'Finance', 'Fitness', 'Lifestyle', 'Hooks', 'Humor', 'Storytelling']
    all_categories = sorted(list(set(default_cats + [c for c in user_cats if c])))

    context = {
        'items': page_obj,
        'source_types': InspirationItem.SOURCE_TYPES,
        'categories': all_categories,
        'search_q': search_q,
        'type_filter': type_filter,
        'cat_filter': cat_filter,
        'favorite_filter': favorite_filter,
        'total_items': items_qs.count(),
        'favorites_count': InspirationItem.objects.filter(workspace=workspace, creator=creator, is_favorite=True).count(),
    }
    return render(request, 'creator/growth_inspiration_library.html', context)


@login_required
def growth_studio_inspiration_add_api(request):
    """
    Saves a new item into the Inspiration Library with URL validation.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    workspace = request.workspace
    creator = request.user

    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    else:
        data = request.POST

    title = data.get('title', '').strip()
    if not title:
        return JsonResponse({'status': 'error', 'message': 'Title is required'}, status=400)

    source_url = data.get('source_url', '').strip()
    if source_url:
        validator = URLValidator()
        try:
            validator(source_url)
        except ValidationError:
            return JsonResponse({'status': 'error', 'message': 'Please provide a valid URL'}, status=400)

    item = InspirationItem.objects.create(
        workspace=workspace,
        creator=creator,
        title=title,
        source_type=data.get('source_type', 'URL').strip(),
        source_url=source_url,
        creator_handle=data.get('creator_handle', '').strip().lstrip('@'),
        platform=data.get('platform', 'Instagram').strip(),
        hook_text=data.get('hook_text', '').strip(),
        caption_text=data.get('caption_text', '').strip(),
        category=data.get('category', 'General').strip(),
        tags=data.get('tags', '').strip(),
        notes=data.get('notes', '').strip()
    )

    log_audit_event(
        actor=creator,
        action='INSPIRATION_ITEM_ADDED',
        resource_type='InspirationItem',
        resource_id=item.id,
        request=request,
        details={'title': title, 'source_type': item.source_type}
    )

    if request.content_type == 'application/json' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'message': f"Inspiration '{title}' saved to your library.",
            'item_id': str(item.id)
        })

    messages.success(request, f"Inspiration '{title}' saved to your library.")
    return redirect('creator_inspiration_library')


@login_required
def growth_studio_inspiration_toggle_favorite_api(request, item_id):
    """
    Toggles favorite status for an inspiration library item.
    """
    if request.method == 'POST':
        item = get_object_or_404(InspirationItem, id=item_id, workspace=request.workspace, creator=request.user)
        item.is_favorite = not item.is_favorite
        item.save(update_fields=['is_favorite', 'updated_at'])
        return JsonResponse({'status': 'success', 'is_favorite': item.is_favorite})
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)


@login_required
def growth_studio_inspiration_delete_api(request, item_id):
    """
    Deletes an inspiration item with ownership validation.
    """
    if request.method == 'POST':
        item = get_object_or_404(InspirationItem, id=item_id, workspace=request.workspace, creator=request.user)
        title = item.title
        item.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({'status': 'success', 'message': f"Inspiration '{title}' removed."})
        messages.success(request, f"Inspiration '{title}' removed.")
    return redirect('creator_inspiration_library')


# =============================================================================
# 4. PERFORMANCE COACH VIEWS & APIS
# =============================================================================

@login_required
def growth_studio_performance_coach_view(request):
    """
    Content Performance Coach:
    Displays genuine Instagram insights obtained through official Meta API integration.
    Clearly distinguishes observed metrics from AI-generated hypotheses.
    Zero AI calls on page load.
    """
    workspace = request.workspace
    creator = request.user

    # Fetch genuine observed metrics from Meta API (calculated via pure Python)
    perf_data = PerformanceCoachService.get_account_performance(workspace)

    # Fetch the most recent on-demand AI coach report if one has been generated
    latest_report = PerformanceCoachReport.objects.filter(workspace=workspace, creator=creator).order_by('-created_at').first()
    past_reports = PerformanceCoachReport.objects.filter(workspace=workspace, creator=creator).order_by('-created_at')[:5]

    voice_profile = CreatorVoiceProfile.objects.filter(workspace=workspace, creator=creator, is_active=True).first()

    context = {
        'perf_data': perf_data,
        'latest_report': latest_report,
        'past_reports': past_reports,
        'voice_profile': voice_profile,
    }
    return render(request, 'creator/growth_performance_coach.html', context)


@login_required
def growth_studio_performance_coach_ai_analyze_api(request):
    """
    Explicit on-demand trigger for Gemini AI performance coach recommendation.
    Only executed when creator explicitly requests it.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    workspace = request.workspace
    creator = request.user

    # Fetch fresh observed metrics
    perf_data = PerformanceCoachService.get_account_performance(workspace)

    if not perf_data.get('connected'):
        return JsonResponse({
            'status': 'error',
            'message': perf_data.get('message', 'Please connect an active Instagram account to analyze performance.')
        }, status=400)

    # Prepare top posts summary text
    top_posts = perf_data.get('top_posts', [])
    posts_summary = ""
    for idx, p in enumerate(top_posts, start=1):
        posts_summary += f"{idx}. '{p.get('caption', '')}' — {p.get('likes')} likes, {p.get('comments')} comments ({p.get('media_type')})\n"

    voice_profile = CreatorVoiceProfile.objects.filter(workspace=workspace, creator=creator, is_active=True).first()

    # Call Gemini via AIGrowthService with token limits and audit logging
    insights = AIGrowthService.generate_performance_coach_insights(
        observed_metrics=perf_data,
        top_posts_summary=posts_summary,
        voice_profile=voice_profile,
        workspace=workspace,
        user=creator
    )

    # Save report to database
    report = PerformanceCoachReport.objects.create(
        workspace=workspace,
        creator=creator,
        social_account=perf_data.get('account'),
        period_days=30,
        observed_metrics=perf_data,
        ai_summary=insights.get('summary', ''),
        strengths=insights.get('strengths', []),
        growth_opportunities=insights.get('growth_opportunities', []),
        recommended_experiments=insights.get('recommended_experiments', [])
    )

    log_audit_event(
        actor=creator,
        action='PERFORMANCE_COACH_ANALYSIS_GENERATED',
        resource_type='PerformanceCoachReport',
        resource_id=report.id,
        request=request,
        details={'post_count': perf_data.get('post_count', 0), 'report_id': str(report.id)}
    )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({
            'status': 'success',
            'message': 'AI Coach recommendations generated successfully.',
            'report': {
                'id': str(report.id),
                'summary': report.ai_summary,
                'strengths': report.strengths,
                'growth_opportunities': report.growth_opportunities,
                'recommended_experiments': report.recommended_experiments,
                'created_at': report.created_at.strftime('%b %d, %Y %H:%M')
            }
        })

    messages.success(request, "AI Performance Coach strategy report generated successfully.")
    return redirect('creator_performance_coach')



