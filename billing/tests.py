from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, Role
from workspaces.models import Workspace
from billing.models import Plan, RegionalPrice, TaxRate, Subscription, CheckoutSession
from billing.services import calculate_checkout, get_regional_price

class RegionalPricingTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='regional_test_user', password='password123', role=Role.CREATOR)
        self.workspace = Workspace.objects.create(name="Regional Test WS", owner=self.user, slug="regional-ws")

        self.plan = Plan.objects.create(name="PRO", slug="pro", price_monthly=99.00)
        RegionalPrice.objects.create(plan=self.plan, region_code='IN', currency='INR', price_monthly=99.00)
        RegionalPrice.objects.create(plan=self.plan, region_code='INTL', currency='USD', price_monthly=5.00)

        TaxRate.objects.create(country_code='IN', tax_name='GST', rate_percent=18.00)
        TaxRate.objects.create(country_code='INTL', tax_name='VAT', rate_percent=0.00)

    def test_india_regional_price_resolution(self):
        pricing = get_regional_price(self.plan, 'IN')
        self.assertEqual(pricing['currency'], 'INR')
        self.assertEqual(float(pricing['amount']), 99.00)

    def test_international_regional_price_resolution(self):
        for country in ['US', 'GB', 'CA', 'AU']:
            pricing = get_regional_price(self.plan, country)
            self.assertEqual(pricing['currency'], 'USD')
            self.assertEqual(float(pricing['amount']), 5.00)

    def test_pricing_quote_api_india(self):
        response = self.client.get(reverse('pricing_quote_api') + '?plan=pro&country=IN')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['currency'], 'INR')
        self.assertEqual(data['subtotal'], 99.00)
        self.assertEqual(data['tax_amount'], 17.82)
        self.assertEqual(data['total'], 116.82)

    def test_pricing_quote_api_international(self):
        response = self.client.get(reverse('pricing_quote_api') + '?plan=pro&country=US')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['currency'], 'USD')
        self.assertEqual(data['subtotal'], 5.00)
        self.assertEqual(data['total'], 5.00)

    def test_security_backend_price_recalculation(self):
        # Client tries sending tampered parameters: price=0.01
        self.client.login(username='regional_test_user', password='password123')
        response = self.client.post(reverse('process_checkout'), {
            'plan_slug': 'pro',
            'billing_country': 'IN',
            'price': '0.01', # Tampered frontend price must be ignored by backend!
            'currency': 'USD' # Tampered frontend currency must be ignored!
        })
        self.assertEqual(response.status_code, 302)
        
        sub = Subscription.objects.get(workspace=self.workspace)
        self.assertEqual(sub.billing_country, 'IN')
        self.assertEqual(sub.billing_currency, 'INR')
        self.assertEqual(float(sub.price_paid), 116.82) # Server recalculated ₹99 + ₹17.82 GST!
