import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from products.models import Product, DigitalProduct

ITEM_TYPE_CHOICES = [
    ('CUSTOM_LINK', 'Custom Link'),
    ('SOCIAL_PROFILE', 'Social Profile'),
    ('VIDEO', 'Video Embed'),
    ('IMAGE', 'Image Block'),
    ('TEXT', 'Text Paragraph'),
    ('HEADING', 'Heading Text'),
    ('DIVIDER', 'Divider Line'),
    ('EMBED', 'Custom Embed'),
    ('PRODUCT', 'Physical Product'),
    ('DIGITAL_PRODUCT', 'Digital Product Download'),
    ('AFFILIATE_PRODUCT', 'Affiliate Product'),
    ('PROMOTION', 'Promotion / Deal'),
    ('CAMPAIGN', 'Brand Campaign'),
    ('CONTACT_FORM', 'Contact / Lead Form'),
    ('EMAIL_SIGNUP', 'Email Newsletter Signup'),
    ('BOOKING', 'Booking / Consultation'),
    ('CUSTOM_CTA', 'Custom Call To Action'),
]

LAYOUT_SIZE_CHOICES = [
    ('FEATURED', 'Featured Large Card'),
    ('STANDARD', 'Standard Card'),
    ('COMPACT', 'Compact Row'),
]

THEME_CHOICES = [
    ('MINIMAL', 'Minimal White'),
    ('CREATOR', 'Creator Blue'),
    ('DARK', 'Dark Mode'),
    ('NEON', 'Neon Glow'),
    ('LUXURY', 'Luxury Gold'),
    ('BUSINESS', 'Business Clean'),
    ('FASHION', 'Fashion Pastel'),
    ('GAMING', 'Gaming Cyber'),
    ('MUSIC', 'Music Dark Wave'),
    ('PODCAST', 'Podcast Clean'),
    ('STORE', 'Storefront Modern'),
    ('PROFESSIONAL', 'Professional Slate'),
]

class LinkHub(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='link_hub')
    username = models.SlugField(max_length=100, unique=True)
    title = models.CharField(max_length=255)
    bio = models.TextField(blank=True, default="")
    avatar_url = models.URLField(blank=True, default="")
    is_verified = models.BooleanField(default=False)
    
    # Theme & Appearance Settings
    theme = models.CharField(max_length=50, choices=THEME_CHOICES, default="MINIMAL")
    bg_type = models.CharField(max_length=20, default="SOLID") # SOLID, GRADIENT, IMAGE
    bg_color = models.CharField(max_length=50, default="#F8FAFC")
    bg_gradient = models.CharField(max_length=100, default="from-slate-900 to-indigo-900")
    bg_image_url = models.URLField(blank=True, default="")
    button_style = models.CharField(max_length=30, default="ROUNDED") # ROUNDED, PILL, SQUARE, OUTLINE, MINIMAL, SHADOW
    button_color = models.CharField(max_length=50, default="#2451FF")
    button_text_color = models.CharField(max_length=50, default="#FFFFFF")
    font_family = models.CharField(max_length=50, default="Inter")
    
    # Social Icon URLs
    social_instagram = models.URLField(blank=True, default="")
    social_facebook = models.URLField(blank=True, default="")
    social_youtube = models.URLField(blank=True, default="")
    social_tiktok = models.URLField(blank=True, default="")
    social_x = models.URLField(blank=True, default="")
    social_linkedin = models.URLField(blank=True, default="")
    social_telegram = models.URLField(blank=True, default="")
    social_whatsapp = models.URLField(blank=True, default="")
    social_github = models.URLField(blank=True, default="")
    social_spotify = models.URLField(blank=True, default="")
    social_website = models.URLField(blank=True, default="")
    
    # SEO & Branding Metadata
    meta_title = models.CharField(max_length=255, blank=True, default="")
    meta_description = models.TextField(blank=True, default="")
    meta_og_image = models.URLField(blank=True, default="")
    custom_domain = models.CharField(max_length=255, blank=True, default="")
    domain_verified = models.BooleanField(default=False)
    
    is_published = models.BooleanField(default=True)
    total_views = models.IntegerField(default=0)
    total_clicks = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"LinkHub @{self.username}"

class LinkHubItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    link_hub = models.ForeignKey(LinkHub, on_delete=models.CASCADE, related_name='items')
    item_type = models.CharField(max_length=30, choices=ITEM_TYPE_CHOICES, default='CUSTOM_LINK')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    url = models.URLField(blank=True, default="")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    digital_product = models.ForeignKey(DigitalProduct, on_delete=models.SET_NULL, null=True, blank=True)
    
    icon = models.CharField(max_length=50, default="link")
    thumbnail_url = models.URLField(blank=True, default="")
    image = models.ImageField(upload_to='linkhub_items/', null=True, blank=True)
    badge_text = models.CharField(max_length=50, blank=True, default="")
    cta_text = models.CharField(max_length=100, blank=True, default="View Link")
    
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    affiliate_marketplace = models.CharField(max_length=100, blank=True, default="")
    
    layout_size = models.CharField(max_length=20, choices=LAYOUT_SIZE_CHOICES, default='STANDARD')
    is_featured = models.BooleanField(default=False)
    position = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    
    # Scheduling fields
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    
    click_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['position']

    def is_currently_visible(self):
        if not self.is_active:
            return False
        now = timezone.now()
        if self.start_time and now < self.start_time:
            return False
        if self.end_time and now > self.end_time:
            return False
        return True

    def __str__(self):
        return f"{self.title} ({self.item_type})"

class LinkView(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    link_hub = models.ForeignKey(LinkHub, on_delete=models.CASCADE, related_name='page_views')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    referrer = models.URLField(blank=True, default="")
    device_type = models.CharField(max_length=30, default="Mobile")
    browser = models.CharField(max_length=50, default="Unknown")
    os = models.CharField(max_length=50, default="Unknown")
    country = models.CharField(max_length=50, default="Unknown")
    source = models.CharField(max_length=50, default="DIRECT")
    
    utm_source = models.CharField(max_length=100, blank=True, default="")
    utm_medium = models.CharField(max_length=100, blank=True, default="")
    utm_campaign = models.CharField(max_length=100, blank=True, default="")
    utm_content = models.CharField(max_length=100, blank=True, default="")
    utm_term = models.CharField(max_length=100, blank=True, default="")
    
    viewed_at = models.DateTimeField(auto_now_add=True)

class LinkClick(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    link_hub_item = models.ForeignKey(LinkHubItem, on_delete=models.CASCADE, related_name='clicks')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    referrer = models.URLField(blank=True, default="")
    device_type = models.CharField(max_length=30, default="Mobile")
    browser = models.CharField(max_length=50, default="Unknown")
    os = models.CharField(max_length=50, default="Unknown")
    country = models.CharField(max_length=50, default="Unknown")
    source = models.CharField(max_length=50, default="DIRECT")
    
    utm_source = models.CharField(max_length=100, blank=True, default="")
    utm_medium = models.CharField(max_length=100, blank=True, default="")
    utm_campaign = models.CharField(max_length=100, blank=True, default="")
    
    clicked_at = models.DateTimeField(auto_now_add=True)

class LinkShortener(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='short_links')
    slug = models.SlugField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    target_url = models.URLField()
    click_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    expiration = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class QRCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='qr_codes')
    title = models.CharField(max_length=255, default="Main Link Hub QR")
    target_url = models.URLField()
    fg_color = models.CharField(max_length=20, default="#101828")
    bg_color = models.CharField(max_length=20, default="#FFFFFF")
    scan_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

class Subscriber(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscribers')
    email = models.EmailField()
    source = models.CharField(max_length=50, default="LINK_HUB")
    consent_given = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('creator', 'email')
