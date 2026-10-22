import uuid
from django.db import models
from workspaces.models import Workspace

class SocialAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='social_accounts')
    platform = models.CharField(max_length=20, choices=[('INSTAGRAM', 'Instagram Business'), ('FACEBOOK', 'Facebook Page')])
    account_id = models.CharField(max_length=255)
    account_name = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    profile_pic = models.URLField(blank=True, default="")
    is_connected = models.BooleanField(default=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    last_sync_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.platform}: @{self.username}"

class MetaToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    social_account = models.OneToOneField(SocialAccount, on_delete=models.CASCADE, related_name='meta_token')
    access_token_encrypted = models.TextField()
    refresh_token_encrypted = models.TextField(blank=True, default="")
    token_type = models.CharField(max_length=50, default="Bearer")
    scope = models.TextField(default="instagram_basic,instagram_manage_comments,instagram_manage_messages,pages_manage_metadata,pages_read_engagement")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class AccountHealth(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    social_account = models.OneToOneField(SocialAccount, on_delete=models.CASCADE, related_name='health')
    meta_status = models.CharField(max_length=20, default='HEALTHY', choices=[('HEALTHY', 'Healthy'), ('WARNING', 'Warning'), ('EXPIRED', 'Token Expired'), ('DISCONNECTED', 'Disconnected')])
    webhook_status = models.CharField(max_length=20, default='ACTIVE', choices=[('ACTIVE', 'Active'), ('FAILING', 'Failing')])
    messaging_status = models.CharField(max_length=20, default='OPERATIONAL', choices=[('OPERATIONAL', 'Operational'), ('RATE_LIMITED', 'Rate Limited')])
    rate_limit_percentage = models.IntegerField(default=12)
    last_error = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)
