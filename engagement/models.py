import uuid
from django.db import models
from django.conf import settings
from workspaces.models import Workspace

class Contact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='contacts')
    username = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255, blank=True, default="")
    platform = models.CharField(max_length=20, choices=[('INSTAGRAM', 'Instagram'), ('FACEBOOK', 'Facebook')], default='INSTAGRAM')
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")
    lead_score = models.IntegerField(default=10)
    tags = models.CharField(max_length=255, blank=True, default="VIP, Lead")
    last_interaction = models.DateTimeField(auto_now=True)
    purchase_count = models.IntegerField(default=0)
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"@{self.username} ({self.platform}) - Score: {self.lead_score}"

class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='conversations')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='conversations')
    platform = models.CharField(max_length=20, default='INSTAGRAM')
    status = models.CharField(max_length=20, choices=[('OPEN', 'Open'), ('CLOSED', 'Closed'), ('HANDOFF', 'Human Handoff')], default='OPEN')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Chat with @{self.contact.username} [{self.status}]"

class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender_type = models.CharField(max_length=20, choices=[('CONTACT', 'Customer'), ('BOT', 'AI Automation'), ('HUMAN', 'Human Agent')])
    content = models.TextField()
    media_url = models.URLField(blank=True, default="")
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    meta_message_id = models.CharField(max_length=255, blank=True, default="")

class Tag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='tags')
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=20, default='#7C3AED') # Purple accent

class LeadScoreRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='score_rules')
    event_type = models.CharField(max_length=50, help_text="COMMENT, DM, PRODUCT_CLICK, CHECKOUT, PURCHASE")
    points = models.IntegerField(default=5)
