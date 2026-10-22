import logging
from decimal import Decimal
from django.utils import timezone
from social.models import SocialAccount, MetaToken
from creator.models import DiscoveredVideo

logger = logging.getLogger(__name__)

class BaseVideoDiscoveryProvider:
    """
    Abstract interface for viral short-form video discovery.
    Can be backed by Meta Graph API, YouTube Data API, or third-party discovery services.
    """
    name = "Base Provider"

    def is_configured(self, workspace=None):
        raise NotImplementedError

    def search_videos(self, workspace, niche="General", keywords="", language="", date_range=""):
        raise NotImplementedError


class MetaInstagramDiscoveryProvider(BaseVideoDiscoveryProvider):
    """
    Official Meta Instagram Graph API discovery provider.
    Accesses verified media published by connected business accounts or permitted hashtags.
    """
    name = "Instagram Graph API"

    def is_configured(self, workspace=None):
        if not workspace:
            return False
        # Check if workspace has an active Instagram business account with token
        account = SocialAccount.objects.filter(workspace=workspace, platform='INSTAGRAM', is_connected=True).first()
        return bool(account and hasattr(account, 'meta_token') and account.meta_token.access_token_encrypted)

    def search_videos(self, workspace, niche="General", keywords="", language="", date_range=""):
        if not self.is_configured(workspace):
            return {
                "status": "REQUIRES_SETUP",
                "message": (
                    "Meta Instagram account is not connected. "
                    "Connect your Instagram Professional / Creator account in Social Accounts "
                    "to discover and analyze breakout reels directly from your accounts."
                ),
                "videos": []
            }

        # Query existing discovered videos stored in workspace or query Graph API
        videos = DiscoveredVideo.objects.filter(workspace=workspace, source_provider="INSTAGRAM_GRAPH")
        if niche and niche != "All":
            videos = videos.filter(niche__iexact=niche)
        return {
            "status": "CONNECTED",
            "message": "Connected via Instagram Graph API",
            "videos": list(videos)
        }


class BreakoutScoringEngine:
    """
    Transparent mathematical calculation of breakout performance relative to creator baseline.
    """

    @classmethod
    def calculate_score(cls, views_count, likes_count, comments_count, creator_avg_views=0):
        views = max(0, int(views_count))
        likes = max(0, int(likes_count))
        comments = max(0, int(comments_count))
        avg_views = max(0, int(creator_avg_views))

        if avg_views > 0:
            ratio = round(Decimal(str(views)) / Decimal(str(avg_views)), 2)
            has_baseline = True

            if ratio >= Decimal('5.0'):
                score = Decimal('98.0')
                label = "🚀 Mega Viral Breakout (5x+ Baseline)"
                explanation = f"Video has generated {ratio}x the creator's standard average viewership ({views:,} vs typical {avg_views:,}). Exceptional retention and shareability."
            elif ratio >= Decimal('3.0'):
                score = Decimal('91.5')
                label = "🔥 High Breakout (3x+ Baseline)"
                explanation = f"Outperforming channel baseline by {ratio}x ({views:,} views vs {avg_views:,} avg). Algorithm has expanded delivery beyond primary follower base."
            elif ratio >= Decimal('1.8'):
                score = Decimal('82.0')
                label = "📈 Rising Breakout (1.8x+ Baseline)"
                explanation = f"Performing {ratio}x above creator normal benchmark. Demonstrates strong early completion rate."
            elif ratio >= Decimal('1.2'):
                score = Decimal('70.0')
                label = "⭐ Above Average"
                explanation = f"Performing moderately above baseline ({ratio}x average). Solid hook with consistent engagement."
            else:
                score = Decimal('55.0')
                label = "📊 Typical Channel Performance"
                explanation = f"Views are in line with creator usual average ({ratio}x). Steady audience interaction."

        else:
            # Fallback when historical creator baseline is not available
            has_baseline = False
            ratio = Decimal('1.0')
            engagement_count = likes + comments
            engagement_rate = round((Decimal(str(engagement_count)) / Decimal(str(max(1, views)))) * Decimal('100.0'), 2) if views > 0 else Decimal('0.0')

            if engagement_rate >= Decimal('10.0'):
                score = Decimal('85.0')
                label = "⭐ High Engagement (Estimated)"
                explanation = f"Engagement rate is {engagement_rate}% ({likes:,} likes, {comments:,} comments on {views:,} views). Strong audience response (No historical creator baseline available)."
            elif engagement_rate >= Decimal('5.0'):
                score = Decimal('72.0')
                label = "📈 Solid Engagement (Estimated)"
                explanation = f"Healthy engagement rate of {engagement_rate}% indicates high viewer interest (Estimated without historical baseline)."
            else:
                score = Decimal('60.0')
                label = "📊 Moderate Engagement (Estimated)"
                explanation = f"Standard {engagement_rate}% engagement rate across {views:,} total views."

        return {
            "breakout_score": score,
            "breakout_ratio": ratio,
            "breakout_label": label,
            "breakout_explanation": explanation,
            "has_historical_baseline": has_baseline
        }


class ViralDiscoveryService:
    """
    High-level facade coordinating video discovery, manual reel imports, and breakout analytics.
    """

    @classmethod
    def get_provider_status(cls, workspace):
        meta_provider = MetaInstagramDiscoveryProvider()
        is_meta = meta_provider.is_configured(workspace)

        return {
            "meta_connected": is_meta,
            "active_provider_name": "Instagram Graph API" if is_meta else "Manual Video & Reel Import Engine",
            "message": (
                "Verified Meta Graph API connected" if is_meta
                else "External automated scraper not configured. Connect your Meta account in Social Accounts or use Instant Reel Analyzer below to analyze any public video."
            )
        }

    @classmethod
    def import_and_score_video(cls, workspace, video_url, creator_name, creator_handle="",
                               title="", caption="", transcript="", niche="General",
                               views_count=0, likes_count=0, comments_count=0, creator_avg_views=0):
        """
        Registers a reference video with transparent breakout scoring and persists to DiscoveredVideo.
        """
        metrics = BreakoutScoringEngine.calculate_score(
            views_count=views_count,
            likes_count=likes_count,
            comments_count=comments_count,
            creator_avg_views=creator_avg_views
        )

        clean_handle = creator_handle.replace('@', '').strip() or creator_name.lower().replace(' ', '')
        profile_url = f"https://instagram.com/{clean_handle}" if not creator_handle.startswith('http') else creator_handle

        video = DiscoveredVideo.objects.create(
            workspace=workspace,
            video_id=f"vid_{int(timezone.now().timestamp())}_{clean_handle[:10]}",
            source_provider="MANUAL_INPUT",
            source_url=video_url,
            thumbnail_url="https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=600&auto=format&fit=crop&q=80",
            creator_name=creator_name,
            creator_handle=clean_handle,
            creator_profile_url=profile_url,
            title=title or (caption[:60] + "..." if len(caption) > 60 else caption) or f"Reel by @{clean_handle}",
            caption=caption,
            transcript=transcript,
            niche=niche,
            published_at=timezone.now(),
            views_count=int(views_count),
            likes_count=int(likes_count),
            comments_count=int(comments_count),
            creator_avg_views=int(creator_avg_views),
            breakout_score=metrics['breakout_score'],
            breakout_ratio=metrics['breakout_ratio'],
            breakout_label=metrics['breakout_label'],
            breakout_explanation=metrics['breakout_explanation'],
            has_historical_baseline=metrics['has_historical_baseline']
        )
        return video
