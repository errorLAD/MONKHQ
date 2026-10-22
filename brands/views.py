from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta

from promotions.models import Promotion, PromotionApplication, PromotionInterest, BrandDeal
from accounts.models import User, Role
from creator.models import CreatorProfile
from products.models import Product
from orders.models import Order, RevenueEvent
from campaigns.models import Campaign
from engagement.models import Conversation
from billing.models import Subscription, Plan
from audit.services import log_audit_event

@login_required
def brand_dashboard_view(request):
    workspace = request.workspace
    promotions = Promotion.objects.filter(brand=request.user)
    applications = PromotionApplication.objects.filter(promotion__brand=request.user)
    interested = PromotionInterest.objects.filter(promotion__brand=request.user)
    deals = BrandDeal.objects.filter(brand=request.user)
    
    orders = Order.objects.filter(workspace=workspace)
    total_sales = orders.count()
    revenue = orders.aggregate(total=Sum('total_amount'))['total'] or 0.00
    
    context = {
        'total_promotions': promotions.count(),
        'active_promotions': promotions.filter(status='PUBLISHED').count(),
        'total_applications': applications.count(),
        'interested_creators_count': interested.count(),
        'active_deals': deals.count(),
        'total_sales': total_sales,
        'revenue': revenue,
        'recent_applications': applications.order_by('-submitted_at')[:5],
    }
    return render(request, 'brands/dashboard.html', context)

@login_required
def brand_promotions_list_view(request):
    promotions = Promotion.objects.filter(brand=request.user).order_by('-created_at')
    return render(request, 'brands/promotions_list.html', {'promotions': promotions})

@login_required
def brand_promotions_create_view(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        category = request.POST.get('category', 'Fashion & Lifestyle')
        budget = request.POST.get('budget', 1000)
        min_followers = request.POST.get('min_followers', 5000)
        compensation_type = request.POST.get('compensation_type', 'HYBRID')
        
        promotion = Promotion.objects.create(
            brand=request.user,
            title=title,
            description=description,
            category=category,
            budget=budget,
            min_followers=min_followers,
            compensation_type=compensation_type,
            start_date=timezone.now().date(),
            end_date=(timezone.now() + timedelta(days=30)).date(),
            status='PUBLISHED'
        )
        log_audit_event(actor=request.user, action='BRAND_PROMOTION_CREATED', resource_type='Promotion', resource_id=promotion.id, request=request)
        messages.success(request, f"Promotion '{title}' published to Creator Marketplace!")
        return redirect('brand_promotions_list')
        
    return render(request, 'brands/promotions_create.html')

@login_required
def brand_applications_view(request):
    applications = PromotionApplication.objects.filter(promotion__brand=request.user).order_by('-submitted_at')
    if request.method == 'POST':
        app_id = request.POST.get('application_id')
        action = request.POST.get('action') # accept or reject
        app = get_object_or_404(PromotionApplication, id=app_id, promotion__brand=request.user)
        if action == 'accept':
            app.status = 'ACCEPTED'
            app.save()
            BrandDeal.objects.create(
                brand=request.user,
                creator=app.creator,
                promotion=app.promotion,
                agreed_amount=app.requested_amount,
                status='ACCEPTED'
            )
            messages.success(request, f"Application by @{app.creator.username} accepted! Deal created.")
        elif action == 'reject':
            app.status = 'REJECTED'
            app.save()
            messages.info(request, f"Application by @{app.creator.username} rejected.")
        return redirect('brand_applications')
        
    return render(request, 'brands/applications.html', {'applications': applications})

@login_required
def brand_interested_view(request):
    interests = PromotionInterest.objects.filter(promotion__brand=request.user).order_by('-created_at')
    return render(request, 'brands/interested.html', {'interests': interests})

@login_required
def brand_creators_find_view(request):
    creators = CreatorProfile.objects.all().select_related('user')
    return render(request, 'brands/creators_find.html', {'creators': creators})

@login_required
def brand_campaigns_view(request):
    campaigns = Campaign.objects.filter(workspace=request.workspace)
    return render(request, 'brands/campaigns.html', {'campaigns': campaigns})

@login_required
def brand_products_view(request):
    products = Product.objects.filter(workspace=request.workspace)
    return render(request, 'brands/products.html', {'products': products})

@login_required
def brand_orders_view(request):
    orders = Order.objects.filter(workspace=request.workspace)
    return render(request, 'brands/orders.html', {'orders': orders})

@login_required
def brand_revenue_view(request):
    revenue_events = RevenueEvent.objects.filter(brand=request.user)
    return render(request, 'brands/revenue.html', {'revenue_events': revenue_events})

@login_required
def brand_analytics_view(request):
    return render(request, 'brands/analytics.html')

@login_required
def brand_ai_view(request):
    return render(request, 'brands/ai.html')

@login_required
def brand_inbox_view(request):
    conversations = Conversation.objects.filter(workspace=request.workspace)
    return render(request, 'brands/inbox.html', {'conversations': conversations})

@login_required
def brand_linkhub_view(request):
    return render(request, 'brands/linkhub.html')

@login_required
def brand_billing_view(request):
    plans = Plan.objects.filter(is_active=True)
    sub = Subscription.objects.filter(workspace=request.workspace).first()
    return render(request, 'brands/billing.html', {'plans': plans, 'subscription': sub})

@login_required
def brand_settings_view(request):
    if request.method == 'POST':
        company_name = request.POST.get('company_name')
        industry = request.POST.get('industry')
        if hasattr(request.user, 'brand_profile'):
            profile = request.user.brand_profile
            profile.company_name = company_name
            profile.industry = industry
            profile.save()
        messages.success(request, "Brand settings updated.")
        return redirect('brand_settings')
    return render(request, 'brands/settings.html')
