import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class Role(models.TextChoices):
    CREATOR = 'CREATOR', _('Creator')
    BRAND = 'BRAND', _('Brand')
    PLATFORM_ADMIN = 'PLATFORM_ADMIN', _('Platform Admin')

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CREATOR)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    login_ip = models.GenericIPAddressField(null=True, blank=True)
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_creator(self):
        return self.role == Role.CREATOR

    @property
    def is_brand(self):
        return self.role == Role.BRAND

    @property
    def is_platform_admin(self):
        return self.role == Role.PLATFORM_ADMIN or self.is_superuser

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
