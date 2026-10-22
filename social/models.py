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
    scope = models.TextField(default="instagram_business_basic,instagram_business_manage_comments,instagram_business_manage_messages,instagram_content_publish")
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


class InstagramPost(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('IMAGE', 'Single Image Post'),
        ('REEL', 'Instagram Reel / Video'),
        ('CAROUSEL', 'Carousel Post'),
    ]

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('CONTAINER_CREATED', 'Container Created'),
        ('PUBLISHING', 'Publishing'),
        ('PUBLISHED', 'Published'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='instagram_posts')
    social_account = models.ForeignKey(SocialAccount, on_delete=models.CASCADE, related_name='posts')
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPE_CHOICES, default='IMAGE')
    caption = models.TextField(blank=True, default="")
    media_url = models.URLField(max_length=1000, help_text="Publicly accessible HTTPS image or video URL")
    container_id = models.CharField(max_length=255, blank=True, default="")
    instagram_media_id = models.CharField(max_length=255, blank=True, default="")
    permalink = models.URLField(blank=True, default="")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='DRAFT')
    error_message = models.TextField(blank=True, default="")
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"IG Post ({self.media_type}) @{self.social_account.username} [{self.status}]"
