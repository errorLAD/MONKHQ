import uuid
from django.db import models
from django.conf import settings

class BrandProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='brand_profile')
    company_name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='brand_logos/', null=True, blank=True)
    website = models.URLField(blank=True, default="")
    industry = models.CharField(max_length=100, default="E-Commerce")
    company_size = models.CharField(max_length=50, default="10-50")
    description = models.TextField(blank=True, default="")
    verified_brand = models.BooleanField(default=True)

    def __str__(self):
        return f"BrandProfile: {self.company_name}"
