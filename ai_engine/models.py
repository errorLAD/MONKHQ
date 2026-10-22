import uuid
from django.db import models
from workspaces.models import Workspace
from automations.models import Automation

class AIAgent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='ai_agents')
    name = models.CharField(max_length=255, default="SocialFlow Sales Assistant")
    objective = models.CharField(max_length=255, default="Qualify leads and recommend product links")
    tone = models.CharField(max_length=50, default="Friendly, Professional, Helpful")
    instructions = models.TextField(default="Never invent pricing or policy information. Only recommend verified products.")
    is_active = models.BooleanField(default=True)
    escalation_keyword = models.CharField(max_length=100, default="AGENT, HUMAN, HELP")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AI Agent: {self.name}"

class KnowledgeBase(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='knowledge_bases')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"KB: {self.title}"

class KnowledgeDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    knowledge_base = models.ForeignKey(KnowledgeBase, on_delete=models.CASCADE, related_name='documents')
    doc_type = models.CharField(max_length=20, choices=[('TEXT', 'Plain Text'), ('FAQ', 'FAQ Pair'), ('PRODUCT_INFO', 'Product Catalog Info'), ('URL', 'Website URL')], default='TEXT')
    title = models.CharField(max_length=255)
    content = models.TextField()
    source_url = models.URLField(blank=True, default="")

class MessageVariant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    automation = models.ForeignKey(Automation, on_delete=models.CASCADE, related_name='message_variants')
    variant_name = models.CharField(max_length=50, default="Variant A")
    content = models.TextField()
    sent_count = models.IntegerField(default=0)
    response_count = models.IntegerField(default=0)
    conversion_count = models.IntegerField(default=0)

from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

class CommentGuard(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.OneToOneField(Workspace, on_delete=models.CASCADE, related_name='comment_guard')
    max_replies_per_hour = models.IntegerField(default=30)
    max_dms_per_user_day = models.IntegerField(default=3)
    spam_keywords = models.TextField(default="crypto, scam, dm me, follower growth")
    is_active = models.BooleanField(default=True)


class AITokenUsage(models.Model):
    """
    Tracks token consumption, estimated USD costs, cache hits, and status
    for Google Gemini and AI services per user and workspace.
    """
    STATUS_CHOICES = [
        ('SUCCESS', 'Success (API Invoked)'),
        ('CACHED', 'Cached (Zero Token Cost)'),
        ('RATE_LIMITED', 'Rate Limited by Upstream'),
        ('SAFEGUARD_THROTTLED', 'Throttled by User Safeguard'),
        ('FALLBACK_USED', 'Resilient Heuristic Fallback'),
        ('ERROR', 'Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='ai_token_usages', null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_token_usages')
    feature = models.CharField(max_length=100, db_index=True) # e.g. SCRIPT_STUDIO, TRENDING_REEL, NICHE_RELEVANCE
    model_name = models.CharField(max_length=100, default="gemini-3.8-flash")
    prompt_tokens = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    estimated_cost_usd = models.DecimalField(max_digits=12, decimal_places=8, default=Decimal('0.00000000'))
    was_cached = models.BooleanField(default=False)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='SUCCESS')
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['workspace', 'timestamp']),
        ]

    def __str__(self):
        username = self.user.username if self.user else "Anonymous"
        return f"{username} - {self.feature} ({self.total_tokens} tokens, ${self.estimated_cost_usd:.6f})"

    @classmethod
    def calculate_cost(cls, prompt_tokens, completion_tokens, model_name=None):
        """
        Calculates estimated cost in USD using configured token pricing rates.
        Defaults to cost-effective Gemini Flash pricing ($0.075 / 1M input, $0.300 / 1M output).
        """
        cost_in_m = getattr(settings, 'GEMINI_COST_PER_MILLION_INPUT', 0.075)
        cost_out_m = getattr(settings, 'GEMINI_COST_PER_MILLION_OUTPUT', 0.300)

        cost_in = (Decimal(str(prompt_tokens)) / Decimal('1000000')) * Decimal(str(cost_in_m))
        cost_out = (Decimal(str(completion_tokens)) / Decimal('1000000')) * Decimal(str(cost_out_m))
        return (cost_in + cost_out).quantize(Decimal('0.00000001'))

    @classmethod
    def record(cls, workspace=None, user=None, feature="AI_REQUEST", model_name="gemini-3.8-flash",
               prompt_tokens=0, completion_tokens=0, was_cached=False, status='SUCCESS'):
        """
        Persists an AI token usage record with cost calculation.
        """
        total_tokens = prompt_tokens + completion_tokens if not was_cached else 0
        cost = Decimal('0.00000000') if was_cached else cls.calculate_cost(prompt_tokens, completion_tokens, model_name)

        usage = cls.objects.create(
            workspace=workspace,
            user=user,
            feature=feature,
            model_name=model_name,
            prompt_tokens=prompt_tokens if not was_cached else 0,
            completion_tokens=completion_tokens if not was_cached else 0,
            total_tokens=total_tokens,
            estimated_cost_usd=cost,
            was_cached=was_cached,
            status=status
        )
        return usage

    @classmethod
    def check_user_quota(cls, user):
        """
        Evaluates configurable usage safeguards and abuse protection for a user.
        Returns: (allowed: bool, reason: str, wait_seconds: int)
        Legitimate users have high headroom; rapid-fire spam or scrapers are throttled.
        """
        if not user or not user.is_authenticated:
            return True, "", 0

        now = timezone.now()
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)

        max_hourly = getattr(settings, 'GEMINI_MAX_REQUESTS_PER_USER_HOUR', 30)
        max_daily = getattr(settings, 'GEMINI_MAX_REQUESTS_PER_USER_DAY', 120)
        max_daily_tokens = getattr(settings, 'GEMINI_MAX_DAILY_TOKENS_PER_USER', 100000)

        # Count non-cached API attempts in the last hour
        hourly_count = cls.objects.filter(
            user=user,
            timestamp__gte=one_hour_ago,
            was_cached=False
        ).exclude(status__in=['CACHED', 'SAFEGUARD_THROTTLED']).count()

        if hourly_count >= max_hourly:
            return False, f"Hourly AI generation limit ({max_hourly}/hour) reached. Please wait a few minutes before trying again.", 300

        # Check 24h count & tokens
        daily_records = cls.objects.filter(
            user=user,
            timestamp__gte=one_day_ago,
            was_cached=False
        ).exclude(status__in=['CACHED', 'SAFEGUARD_THROTTLED'])

        daily_count = daily_records.count()
        if daily_count >= max_daily:
            return False, f"Daily AI generation limit ({max_daily}/day) reached. Quota resets in 24 hours.", 3600

        daily_tokens = sum(r.total_tokens for r in daily_records)
        if daily_tokens >= max_daily_tokens:
            return False, f"Daily AI token budget ({max_daily_tokens:,} tokens) reached to protect your account. Quota resets in 24 hours.", 3600

        return True, "", 0

    @classmethod
    def get_user_stats(cls, user, hours=24):
        """
        Aggregates token count, cost, requests, and cache savings for a creator.
        """
        if not user or not user.is_authenticated:
            return {'total_requests': 0, 'total_tokens': 0, 'total_cost_usd': 0.0, 'cached_requests': 0}

        since = timezone.now() - timedelta(hours=hours)
        records = cls.objects.filter(user=user, timestamp__gte=since)

        total_requests = records.count()
        cached_count = records.filter(was_cached=True).count()
        total_tokens = sum(r.total_tokens for r in records)
        total_cost = sum(float(r.estimated_cost_usd) for r in records)

        return {
            'total_requests': total_requests,
            'cached_requests': cached_count,
            'api_requests': total_requests - cached_count,
            'total_tokens': total_tokens,
            'total_cost_usd': round(total_cost, 6),
            'cache_hit_rate_pct': round((cached_count / total_requests * 100) if total_requests else 0, 1),
        }
