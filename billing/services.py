from decimal import Decimal
from django.shortcuts import get_object_or_404
from billing.models import Plan, RegionalPrice, TaxRate, CheckoutSession, format_currency

def get_region_code(country_code):
    if not country_code:
        return 'IN'
    code = country_code.upper().strip()
    return 'IN' if code == 'IN' else 'INTL'

def get_regional_price(plan, country_code='IN'):
    region_code = get_region_code(country_code)
    regional_price = RegionalPrice.objects.filter(plan=plan, region_code=region_code, is_active=True).first()
    if not regional_price:
        # Fallback to defaults
        if region_code == 'IN':
            currency = 'INR'
            amount = Decimal('99.00')
        else:
            currency = 'USD'
            amount = Decimal('5.00')
    else:
        currency = regional_price.currency
        amount = regional_price.price_monthly

    return {
        'region_code': region_code,
        'currency': currency,
        'amount': amount,
        'display_amount': format_currency(amount, currency)
    }

def get_tax_rate(country_code='IN'):
    code = country_code.upper().strip() if country_code else 'IN'
    tax_rate = TaxRate.objects.filter(country_code=code).first()
    if not tax_rate:
        tax_rate = TaxRate.objects.filter(country_code='INTL').first()
    if not tax_rate:
        return {'tax_name': 'Tax', 'rate_percent': Decimal('0.00')}
    return {'tax_name': tax_rate.tax_name, 'rate_percent': tax_rate.rate_percent}

def calculate_checkout(plan_slug, country_code='IN', user=None, workspace=None):
    plan = get_object_or_404(Plan, slug=plan_slug)
    pricing = get_regional_price(plan, country_code)
    tax_info = get_tax_rate(country_code)

    subtotal = Decimal(str(pricing['amount']))
    rate_percent = Decimal(str(tax_info['rate_percent']))
    tax_amount = round(subtotal * (rate_percent / Decimal('100.00')), 2)
    total = subtotal + tax_amount

    currency = pricing['currency']
    return {
        'plan': plan,
        'country': country_code.upper() if country_code else 'IN',
        'region_code': pricing['region_code'],
        'currency': currency,
        'subtotal': subtotal,
        'display_subtotal': format_currency(subtotal, currency),
        'tax_name': tax_info['tax_name'],
        'tax_rate_percent': rate_percent,
        'tax_amount': tax_amount,
        'display_tax_amount': format_currency(tax_amount, currency),
        'total': total,
        'display_total': format_currency(total, currency)
    }
