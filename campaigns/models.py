import uuid
from django.db import models
from django.conf import settings
from workspaces.models import Workspace

class Campaign(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='campaigns')
    name = models.CharField(max_length=255)
    objective = models.CharField(max_length=100, default='Lead Generation')
    budget = models.DecimalField(max_digits=10, decimal_places=2, default=1000.00)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=[('ACTIVE', 'Active'), ('PAUSED', 'Paused'), ('COMPLETED', 'Completed')], default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Campaign: {self.name}"

class Coupon(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='coupons')
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=[('PERCENTAGE', 'Percentage (%)'), ('FIXED', 'Fixed ($)')], default='PERCENTAGE')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=15.00)
    max_uses = models.IntegerField(default=500)
    used_count = models.IntegerField(default=0)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name='coupons')
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Coupon: {self.code} ({self.discount_value})"
