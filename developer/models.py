import uuid
from django.db import models
from workspaces.models import Workspace

class APIKey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='api_keys')
    name = models.CharField(max_length=100)
    key_prefix = models.CharField(max_length=12) # e.g. sf_live_abc1
    hashed_key = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"API Key: {self.name} ({self.key_prefix}...)"

class WebhookEndpoint(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='webhook_endpoints')
    target_url = models.URLField()
    secret = models.CharField(max_length=255)
    events = models.CharField(max_length=255, default="order.created,lead.captured,automation.executed")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Webhook: {self.target_url}"

class WebhookEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name='webhook_events')
    event_type = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    status_code = models.IntegerField(default=200)
    response_body = models.TextField(blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)
    error = models.TextField(blank=True, default="")
