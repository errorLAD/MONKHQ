import uuid
from django.db import models
from django.conf import settings
from workspaces.models import Workspace

class ProductType(models.TextChoices):
    PHYSICAL = 'PHYSICAL', 'Physical Product'
    DIGITAL = 'DIGITAL', 'Digital Product'
    AFFILIATE = 'AFFILIATE', 'Affiliate Product'

class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='products')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_products')
    brand = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='brand_products')
    product_type = models.CharField(max_length=20, choices=ProductType.choices, default=ProductType.PHYSICAL)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True, default="")
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sku = models.CharField(max_length=100, blank=True, default="")
    currency = models.CharField(max_length=10, default="USD")
    inventory = models.IntegerField(default=100)
    external_url = models.URLField(blank=True, default="")
    affiliate_url = models.URLField(blank=True, default="")
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00) # e.g. 10%
    status = models.CharField(max_length=20, choices=[('ACTIVE', 'Active'), ('DRAFT', 'Draft'), ('ARCHIVED', 'Archived')], default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (${self.price})"

class DigitalProduct(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='digital_details')
    file = models.FileField(upload_to='digital_products/')
    file_type = models.CharField(max_length=20, choices=[('PDF', 'PDF Document'), ('ZIP', 'ZIP Archive'), ('VIDEO', 'Video Course'), ('AUDIO', 'Audio File')])
    file_size_mb = models.DecimalField(max_digits=8, decimal_places=2, default=5.00)
    access_limit = models.IntegerField(default=5) # download limit
    download_count = models.IntegerField(default=0)

    def __str__(self):
        return f"Digital: {self.product.name} ({self.file_type})"

class AffiliateLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='affiliate_links')
    title = models.CharField(max_length=255)
    url = models.URLField()
    platform_name = models.CharField(max_length=100, default="Amazon") # e.g. Amazon, Flipkart
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    click_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.platform_name})"
