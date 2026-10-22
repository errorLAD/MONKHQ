import uuid
from django.db import models
from django.conf import settings
from workspaces.models import Workspace

REGIONAL_CODES = [
    ('IN', 'India'),
    ('INTL', 'International / Rest of World'),
]

CURRENCY_CHOICES = [
    ('INR', 'Indian Rupee (₹)'),
    ('USD', 'US Dollar ($)'),
]

def format_currency(amount, currency='INR'):
    try:
        val = float(amount)
        if currency == 'INR':
            return f"₹{val:,.2f}".replace('.00', '')
        elif currency == 'USD':
            return f"${val:,.2f}".replace('.00', '')
        return f"{currency} {val:,.2f}"
    except Exception:
        return f"{currency} {amount}"

class Plan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100) # STARTER, PRO, BUSINESS, ENTERPRISE
    slug = models.SlugField(unique=True)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    max_automations = models.IntegerField(default=5)
    max_monthly_dms = models.IntegerField(default=1000)
    max_link_hubs = models.IntegerField(default=1)
    has_ai_agent = models.BooleanField(default=True)
    has_retrigger_engine = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Plan: {self.name}"

class RegionalPrice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='regional_prices')
    region_code = models.CharField(max_length=10, choices=REGIONAL_CODES, default='IN')
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='INR')
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=99.00)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=990.00)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('plan', 'region_code')

    def __str__(self):
        return f"{self.plan.name} [{self.region_code}]: {format_currency(self.price_monthly, self.currency)}/mo"

    @property
    def display_price(self):
        return format_currency(self.price_monthly, self.currency)

class TaxRate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    country_code = models.CharField(max_length=5, default='IN', unique=True) # IN for India, INTL for Default
    tax_name = models.CharField(max_length=50, default='GST')
    rate_percent = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)

    def __str__(self):
        return f"{self.country_code} - {self.tax_name} ({self.rate_percent}%)"

class Subscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.OneToOneField(Workspace, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='subscriptions')
    billing_country = models.CharField(max_length=5, default='IN')
    billing_currency = models.CharField(max_length=3, default='INR')
    price_paid = models.DecimalField(max_digits=10, decimal_places=2, default=99.00)
    status = models.CharField(max_length=20, choices=[
        ('ACTIVE', 'Active'),
        ('TRIALING', 'Trialing'),
        ('PAST_DUE', 'Past Due'),
        ('CANCELED', 'Canceled')
    ], default='ACTIVE')
    current_period_start = models.DateTimeField(auto_now_add=True)
    current_period_end = models.DateTimeField()

    def __str__(self):
        return f"Sub: {self.workspace.name} -> {self.plan.name} [{self.billing_country}] ({self.status})"

class CheckoutSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='checkout_sessions')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='checkout_sessions')
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    country = models.CharField(max_length=5, default='IN')
    currency = models.CharField(max_length=3, default='INR')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('EXPIRED', 'Expired')
    ], default='PENDING')
    idempotency_key = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Checkout #{str(self.id)[:8]} - {format_currency(self.total, self.currency)} ({self.status})"

class UsageRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='usage_records')
    metric_name = models.CharField(max_length=50) # 'dms_sent', 'leads_generated', 'api_calls'
    quantity = models.IntegerField(default=1)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.workspace.name} - {self.metric_name}: +{self.quantity}"
