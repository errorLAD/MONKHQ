import uuid
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta

from billing.models import Plan, RegionalPrice, Subscription, CheckoutSession, TaxRate, format_currency
from billing.services import calculate_checkout, get_regional_price
from audit.services import log_audit_event

def pricing_quote_api(request):
    country = request.GET.get('country', 'IN').strip().upper()
    plan_slug = request.GET.get('plan', 'pro').strip()

    checkout_data = calculate_checkout(plan_slug=plan_slug, country_code=country)

    return JsonResponse({
        'plan': checkout_data['plan'].name,
        'plan_slug': checkout_data['plan'].slug,
        'country': checkout_data['country'],
        'region': checkout_data['region_code'],
        'currency': checkout_data['currency'],
        'subtotal': float(checkout_data['subtotal']),
        'display_subtotal': checkout_data['display_subtotal'],
        'tax_name': checkout_data['tax_name'],
        'tax_rate_percent': float(checkout_data['tax_rate_percent']),
        'tax_amount': float(checkout_data['tax_amount']),
        'display_tax_amount': checkout_data['display_tax_amount'],
        'total': float(checkout_data['total']),
        'display_total': checkout_data['display_total'],
        'billing_period': 'month'
    })

@login_required
def checkout_view(request):
    plan_slug = request.GET.get('plan', 'pro')
    country = request.GET.get('country', 'IN')

    checkout_data = calculate_checkout(plan_slug=plan_slug, country_code=country, user=request.user, workspace=request.workspace)

    context = {
        'checkout': checkout_data,
        'selected_country': country.upper()
    }
    return render(request, 'billing/checkout.html', context)

@login_required
def process_checkout_view(request):
    if request.method == 'POST':
        plan_slug = request.POST.get('plan_slug', 'pro')
        country = request.POST.get('billing_country', 'IN')
        
        # SERVER-SIDE RECALCULATION & SECURITY: Ignore frontend price
        checkout_data = calculate_checkout(plan_slug=plan_slug, country_code=country, user=request.user, workspace=request.workspace)

        idempotency_key = f"chk_{request.user.id}_{checkout_data['plan'].slug}_{int(timezone.now().timestamp())}"

        session = CheckoutSession.objects.create(
            user=request.user,
            workspace=request.workspace,
            plan=checkout_data['plan'],
            country=checkout_data['country'],
            currency=checkout_data['currency'],
            subtotal=checkout_data['subtotal'],
            tax_amount=checkout_data['tax_amount'],
            total=checkout_data['total'],
            status='COMPLETED',
            idempotency_key=idempotency_key
        )

        # Update / Create Subscription
        now = timezone.now()
        sub, _ = Subscription.objects.get_or_create(
            workspace=request.workspace,
            defaults={
                'plan': checkout_data['plan'],
                'current_period_end': now + timedelta(days=30)
            }
        )
        sub.plan = checkout_data['plan']
        sub.billing_country = checkout_data['country']
        sub.billing_currency = checkout_data['currency']
        sub.price_paid = checkout_data['total']
        sub.status = 'ACTIVE'
        sub.current_period_end = now + timedelta(days=30)
        sub.save()

        log_audit_event(
            actor=request.user,
            action='SUBSCRIPTION_ACTIVATED',
            resource_type='Subscription',
            resource_id=sub.id,
            request=request,
            details={
                'country': checkout_data['country'],
                'currency': checkout_data['currency'],
                'total_paid': str(checkout_data['total']),
                'plan': checkout_data['plan'].name
            }
        )

        messages.success(
            request,
            f"Successfully subscribed to {checkout_data['plan'].name} for {checkout_data['display_total']} ({checkout_data['country']})!"
        )
        
        if request.user.is_creator:
            return redirect('creator_dashboard')
        return redirect('brand_dashboard')

    return redirect('creator_billing')

@csrf_exempt
def payment_webhook_view(request):
    if request.method == 'POST':
        try:
            payload = json.loads(request.body.decode('utf-8'))
            idempotency_key = payload.get('idempotency_key')
            if idempotency_key:
                chk = CheckoutSession.objects.filter(idempotency_key=idempotency_key).first()
                if chk:
                    chk.status = 'COMPLETED'
                    chk.save()
                    return JsonResponse({'status': 'ALREADY_PROCESSED'}, status=200)
            return JsonResponse({'status': 'WEBHOOK_PROCESSED'}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return HttpResponse('Method Not Allowed', status=405)
