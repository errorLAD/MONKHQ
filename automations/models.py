import uuid
from django.db import models
from django.conf import settings
from workspaces.models import Workspace

class TriggerType(models.TextChoices):
    COMMENT = 'INSTAGRAM_COMMENT', 'Instagram / Facebook Comment'
    KEYWORD = 'KEYWORD_DETECTED', 'Keyword Detected'
    DM_RECEIVED = 'DM_RECEIVED', 'DM Received'
    NEW_FOLLOWER = 'NEW_FOLLOWER', 'New Follower'
    STORY_INTERACTION = 'STORY_INTERACTION', 'Story Interaction'
    PRODUCT_CLICK = 'PRODUCT_CLICK', 'Product Click'
    LEAD_CREATED = 'LEAD_CREATED', 'Lead Created'
    ORDER_CREATED = 'ORDER_CREATED', 'Order Created'
    PROMOTION_INTEREST = 'PROMOTION_INTEREST', 'Promotion Interest'

class ActionType(models.TextChoices):
    SEND_DM = 'SEND_DM', 'Send DM'
    SEND_PRODUCT_LINK = 'SEND_PRODUCT_LINK', 'Send Product Link'
    SEND_DIGITAL_PRODUCT = 'SEND_DIGITAL_PRODUCT', 'Send Digital Product'
    SEND_AFFILIATE_LINK = 'SEND_AFFILIATE_LINK', 'Send Affiliate Link'
    SEND_COUPON = 'SEND_COUPON', 'Send Coupon'
    ADD_LEAD_SCORE = 'ADD_LEAD_SCORE', 'Add Lead Score'
    TAG_CONTACT = 'TAG_CONTACT', 'Tag Contact'
    HUMAN_HANDOFF = 'HUMAN_HANDOFF', 'Handoff to Human'
    CREATE_ORDER = 'CREATE_ORDER', 'Create Order'

class AutomationStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    PAUSED = 'PAUSED', 'Paused'
    DRAFT = 'DRAFT', 'Draft'
    ERROR = 'ERROR', 'Error'
    ARCHIVED = 'ARCHIVED', 'Archived'

class AutomationType(models.TextChoices):
    COMMENT_DM = 'COMMENT_DM', 'Comment to DM'
    AI_SALES = 'AI_SALES', 'AI Sales Automation'
    RETRIGGER = 'RETRIGGER', 'Re-trigger Engine'
    FOLLOW = 'FOLLOW', 'New Follower DM'
    PRODUCT = 'PRODUCT', 'Product Link'
    LEAD = 'LEAD', 'Lead Generation'
    PROMOTION = 'PROMOTION', 'Promotion Interest'
    CUSTOM = 'CUSTOM', 'Custom Workflow'

class Automation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='automations')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='automations')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=AutomationStatus.choices, default=AutomationStatus.ACTIVE)
    automation_type = models.CharField(max_length=30, choices=AutomationType.choices, default=AutomationType.COMMENT_DM)
    trigger_type = models.CharField(max_length=50, choices=TriggerType.choices, default=TriggerType.COMMENT)
    is_active = models.BooleanField(default=True)
    execution_count = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    leads_generated = models.IntegerField(default=0)
    revenue_attributed = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    cooldown_seconds = models.IntegerField(default=60) # Cooldown per user
    last_executed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Automation: {self.name} ({self.status})"

class AutomationTrigger(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    automation = models.OneToOneField(Automation, on_delete=models.CASCADE, related_name='trigger')
    event_type = models.CharField(max_length=50, choices=TriggerType.choices, default=TriggerType.COMMENT)
    keywords = models.TextField(help_text="Comma-separated keywords like PRICE, LINK, BUY")
    match_type = models.CharField(max_length=20, choices=[('EXACT', 'Exact Match'), ('CONTAINS', 'Contains Keyword'), ('REGEX', 'Regex')], default='CONTAINS')
    post_id = models.CharField(max_length=255, blank=True, default="ALL_POSTS")

class AutomationCondition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    automation = models.ForeignKey(Automation, on_delete=models.CASCADE, related_name='conditions')
    condition_type = models.CharField(max_length=50, choices=[('KEYWORD', 'Keyword Match'), ('LEAD_SCORE', 'Lead Score Greater Than'), ('PREVIOUS_BUYER', 'Is Previous Buyer')])
    operator = models.CharField(max_length=20, default='EQUALS')
    value = models.CharField(max_length=255)

class AutomationAction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    automation = models.ForeignKey(Automation, on_delete=models.CASCADE, related_name='actions')
    action_type = models.CharField(max_length=50, choices=ActionType.choices, default=ActionType.SEND_DM)
    payload = models.JSONField(default=dict, help_text="Message text, product_id, coupon_code, etc.")
    sequence_order = models.IntegerField(default=1)

class AutomationExecution(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    automation = models.ForeignKey(Automation, on_delete=models.CASCADE, related_name='executions')
    trigger_event_id = models.CharField(max_length=255, blank=True, default="")
    contact_username = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=[('PENDING', 'Pending'), ('SUCCESS', 'Success'), ('FAILED', 'Failed')], default='SUCCESS')
    executed_at = models.DateTimeField(auto_now_add=True)
    duration_seconds = models.DecimalField(max_digits=6, decimal_places=2, default=1.20)
    error_message = models.TextField(blank=True, default="")

class AutomationLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    automation = models.ForeignKey(Automation, on_delete=models.CASCADE, related_name='logs')
    execution = models.ForeignKey(AutomationExecution, on_delete=models.SET_NULL, null=True, blank=True)
    level = models.CharField(max_length=20, default='INFO')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

class AISalesAgent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='ai_sales_agents')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_sales_agents')
    agent_name = models.CharField(max_length=255, default="Alex AI Sales Assistant")
    tone = models.CharField(max_length=50, default="Friendly & Conversational")
    instructions = models.TextField(blank=True, default="Guide social users to product links and assist with purchases based on database pricing.")
    goals = models.TextField(blank=True, default="Drive storefront conversions and answer customer inquiries accurately.")
    knowledge_base = models.TextField(blank=True, default="SocialFlow Creator Storefront products, pricing, shipping, and digital download links.")
    mode = models.CharField(max_length=20, choices=[('ASSISTED', 'Assisted (Human Approval)'), ('AUTOMATIC', 'Fully Automatic AI')], default='AUTOMATIC')
    is_active = models.BooleanField(default=True)
    conversations_count = models.IntegerField(default=142)
    ai_responses_count = models.IntegerField(default=389)
    human_handoffs_count = models.IntegerField(default=4)
    leads_count = models.IntegerField(default=48)
    conversions_count = models.IntegerField(default=22)
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=2450.00)
    created_at = models.DateTimeField(auto_now_add=True)

class AutomationTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=50, default="Social Commerce")
    trigger_type = models.CharField(max_length=50, default="INSTAGRAM_COMMENT")
    action_type = models.CharField(max_length=50, default="SEND_DM")
    default_keywords = models.CharField(max_length=255, default="PRICE, LINK, BUY")
    default_dm_text = models.TextField(default="Hey! Here is your requested product link: https://socialflow.ai/@creator")
    icon = models.CharField(max_length=50, default="zap")
    created_at = models.DateTimeField(auto_now_add=True)
