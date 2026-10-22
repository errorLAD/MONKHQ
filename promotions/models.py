import uuid
from django.db import models
from django.conf import settings

class PromotionStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    PUBLISHED = 'PUBLISHED', 'Published'
    ACTIVE = 'ACTIVE', 'Active'
    PAUSED = 'PAUSED', 'Paused'
    COMPLETED = 'COMPLETED', 'Completed'
    EXPIRED = 'EXPIRED', 'Expired'

class Promotion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='promotions')
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=100, default='Fashion & Lifestyle')
    campaign_type = models.CharField(max_length=100, default='Reels & Stories')
    budget = models.DecimalField(max_digits=10, decimal_places=2, default=1500.00)
    compensation_type = models.CharField(max_length=50, choices=[('FIXED', 'Fixed Pay'), ('COMMISSION', 'Commission per sale'), ('HYBRID', 'Fixed + Commission')], default='HYBRID')
    deliverables_required = models.TextField(default="1 Instagram Reel, 2 Instagram Stories with link")
    min_followers = models.IntegerField(default=10000)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=PromotionStatus.choices, default=PromotionStatus.PUBLISHED)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Promotion: {self.title} (${self.budget})"

class PromotionInterest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name='interests')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='expressed_interests')
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('promotion', 'creator')

class PromotionApplication(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name='applications')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='promotion_applications')
    pitch = models.TextField()
    requested_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[('PENDING', 'Pending Review'), ('ACCEPTED', 'Accepted'), ('REJECTED', 'Rejected')], default='PENDING')
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"App by {self.creator.username} for {self.promotion.title}"

class BrandDeal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='brand_deals')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='creator_deals')
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name='deals')
    status = models.CharField(max_length=30, choices=[('OFFERED', 'Offered'), ('ACCEPTED', 'Accepted'), ('DELIVERABLES_SUBMITTED', 'Deliverables Submitted'), ('APPROVED', 'Approved'), ('PAID', 'Paid'), ('CANCELLED', 'Cancelled')], default='OFFERED')
    agreed_amount = models.DecimalField(max_digits=10, decimal_places=2)
    deliverable_urls = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Deal: {self.brand.username} x {self.creator.username} (${self.agreed_amount})"
