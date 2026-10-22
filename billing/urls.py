from django.urls import path
from billing import views

urlpatterns = [
    path('api/pricing-quote/', views.pricing_quote_api, name='pricing_quote_api'),
    path('checkout/', views.checkout_view, name='billing_checkout'),
    path('checkout/process/', views.process_checkout_view, name='process_checkout'),
    path('webhooks/payment/', views.payment_webhook_view, name='payment_webhook'),
]
