from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import uuid

from accounts.models import User, Role
from workspaces.models import Workspace, WorkspaceMember
from creator.models import CreatorProfile
from brands.models import BrandProfile
from automations.models import Automation, AutomationTrigger, AutomationAction, AutomationExecution, AutomationLog
from engagement.models import Contact, Conversation, Message, LeadScoreRule, Tag
from ai_engine.models import AIAgent, KnowledgeBase, KnowledgeDocument, CommentGuard, MessageVariant
from promotions.models import Promotion, PromotionApplication, PromotionInterest, BrandDeal
from linkhub.models import LinkHub, LinkHubItem
from products.models import Product, DigitalProduct, AffiliateLink
from orders.models import Order, OrderItem, RevenueEvent
from campaigns.models import Campaign, Coupon
from social.models import SocialAccount, MetaToken, AccountHealth
from developer.models import APIKey, WebhookEndpoint, WebhookEvent
from billing.models import Plan, Subscription, UsageRecord
from audit.services import log_audit_event

class Command(BaseCommand):
    help = 'Seeds database with real production-grade demo data for Creator, Brand, and Platform Admin.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting SocialFlow AI seed_demo data population..."))
        
        # 1. Create Subscription Plans
        starter_plan, _ = Plan.objects.get_or_create(
            slug='starter',
            defaults={
                'name': 'STARTER',
                'price_monthly': 29.00,
                'price_yearly': 290.00,
                'max_automations': 5,
                'max_monthly_dms': 1000,
                'max_link_hubs': 1,
            }
        )
        pro_plan, _ = Plan.objects.get_or_create(
            slug='pro',
            defaults={
                'name': 'PRO',
                'price_monthly': 79.00,
                'price_yearly': 790.00,
                'max_automations': 25,
                'max_monthly_dms': 10000,
                'max_link_hubs': 3,
                'has_ai_agent': True,
                'has_retrigger_engine': True,
            }
        )

        # 2. Create Platform Admin
        admin_user, admin_created = User.objects.get_or_create(
            username='admin_platform',
            defaults={
                'email': 'admin@socialflow.ai',
                'role': Role.PLATFORM_ADMIN,
                'is_staff': True,
                'is_superuser': True,
                'first_name': 'Platform',
                'last_name': 'Admin'
            }
        )
        if admin_created:
            admin_user.set_password('password123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Created Admin: admin_platform / password123"))

        # 3. Create Creator User
        creator_user, creator_created = User.objects.get_or_create(
            username='alex_creator',
            defaults={
                'email': 'alex@creator.com',
                'role': Role.CREATOR,
                'first_name': 'Alex',
                'last_name': 'Rivers'
            }
        )
        if creator_created:
            creator_user.set_password('password123')
            creator_user.save()
            CreatorProfile.objects.create(
                user=creator_user,
                bio="Tech & Lifestyle Creator | 150k+ Followers",
                niche="Technology & Lifestyle",
                instagram_handle="alex_rivers",
                website="https://socialflow.ai/@alex_creator",
                creator_score=92,
                monthly_reach=340000,
                engagement_rate=5.20
            )
            self.stdout.write(self.style.SUCCESS("Created Creator: alex_creator / password123"))

        creator_ws, _ = Workspace.objects.get_or_create(
            slug='alex-creator-workspace',
            defaults={
                'name': "Alex Rivers Creator Hub",
                'owner': creator_user,
                'workspace_type': 'CREATOR',
            }
        )
        Subscription.objects.get_or_create(
            workspace=creator_ws,
            defaults={'plan': pro_plan, 'status': 'ACTIVE', 'current_period_end': timezone.now() + timedelta(days=365)}
        )

        # 4. Create Brand User
        brand_user, brand_created = User.objects.get_or_create(
            username='acme_brand',
            defaults={
                'email': 'partners@acmebrand.com',
                'role': Role.BRAND,
                'first_name': 'Acme',
                'last_name': 'Commerce'
            }
        )
        if brand_created:
            brand_user.set_password('password123')
            brand_user.save()
            BrandProfile.objects.create(
                user=brand_user,
                company_name="Acme Apparel & Audio",
                industry="E-Commerce Fashion & Tech",
                company_size="50-200",
                description="Premium minimal lifestyle apparel and noise-canceling audio gear.",
                verified_brand=True
            )
            self.stdout.write(self.style.SUCCESS("Created Brand: acme_brand / password123"))

        brand_ws, _ = Workspace.objects.get_or_create(
            slug='acme-brand-workspace',
            defaults={
                'name': "Acme Brand Workspace",
                'owner': brand_user,
                'workspace_type': 'BRAND',
            }
        )

        # 5. Populate Social Account & Health
        social_acc, _ = SocialAccount.objects.get_or_create(
            workspace=creator_ws,
            platform='INSTAGRAM',
            defaults={
                'account_id': 'ig_17841400998822',
                'account_name': 'Alex Rivers Official',
                'username': 'alex_rivers',
                'is_connected': True,
            }
        )
        AccountHealth.objects.get_or_create(
            social_account=social_acc,
            defaults={'meta_status': 'HEALTHY', 'webhook_status': 'ACTIVE', 'messaging_status': 'OPERATIONAL'}
        )

        # 6. Populate Products & Digital Assets
        prod_headphone, _ = Product.objects.get_or_create(
            workspace=creator_ws,
            slug='wireless-pro-headphones',
            defaults={
                'name': 'Acme Wireless Pro Headphones',
                'price': 199.99,
                'sale_price': 149.99,
                'product_type': 'PHYSICAL',
                'description': 'Studio quality Active Noise Canceling wireless headphones.',
                'external_url': 'https://amazon.com/dp/B08MOCK123',
                'inventory': 45,
            }
        )

        prod_digital, _ = Product.objects.get_or_create(
            workspace=creator_ws,
            slug='creator-monetization-playbook-2026',
            defaults={
                'name': 'Creator Monetization Playbook 2026',
                'price': 29.99,
                'product_type': 'DIGITAL',
                'description': 'Step-by-step PDF guide to earning $10k/month via IG automated sales.',
            }
        )
        DigitalProduct.objects.get_or_create(
            product=prod_digital,
            defaults={'file_type': 'PDF', 'file_size_mb': 12.4, 'download_count': 184}
        )

        aff_link, _ = AffiliateLink.objects.get_or_create(
            workspace=creator_ws,
            title="My Favorite Camera Gear on Amazon",
            defaults={'url': 'https://amazon.com/shop/alex_rivers', 'platform_name': 'Amazon', 'click_count': 420}
        )

        # 7. Populate Automations & Executions
        auto1, _ = Automation.objects.get_or_create(
            workspace=creator_ws,
            name="Comment 'PRICE' -> Auto DM Discount Link",
            defaults={
                'creator': creator_user,
                'trigger_type': 'INSTAGRAM_COMMENT',
                'is_active': True,
                'execution_count': 128,
                'success_count': 126,
                'error_count': 2
            }
        )
        AutomationTrigger.objects.get_or_create(
            automation=auto1,
            defaults={'keywords': 'PRICE, COST, HOW MUCH, LINK', 'match_type': 'CONTAINS'}
        )
        AutomationAction.objects.get_or_create(
            automation=auto1,
            defaults={'action_type': 'SEND_PRODUCT_LINK', 'payload': {'product_id': str(prod_headphone.id), 'message': 'Hey! Here is your exclusive 25% off link for the Wireless Pro Headphones: https://socialflow.ai/@alex_creator'}}
        )

        for i in range(1, 15):
            exec_item = AutomationExecution.objects.create(
                automation=auto1,
                contact_username=f"fan_user_{i}",
                status='SUCCESS' if i != 3 else 'FAILED',
                executed_at=timezone.now() - timedelta(hours=i*2)
            )
            AutomationLog.objects.create(
                automation=auto1,
                execution=exec_item,
                level='INFO' if i != 3 else 'ERROR',
                message=f"Sent automated DM with product link to @fan_user_{i}" if i != 3 else "Meta Rate Limit Exceeded (retrying via Celery task)"
            )

        # 8. Contacts & Unified Inbox Conversations
        for i in range(1, 8):
            contact, _ = Contact.objects.get_or_create(
                workspace=creator_ws,
                username=f"customer_ig_{i}",
                defaults={
                    'full_name': f"Customer {i}",
                    'platform': 'INSTAGRAM',
                    'email': f"customer{i}@example.com",
                    'lead_score': 15 + (i * 10),
                    'tags': 'Hot Lead, Buyer' if i > 4 else 'New Lead',
                    'purchase_count': 1 if i > 4 else 0,
                    'total_spent': 149.99 if i > 4 else 0.00
                }
            )
            conv, _ = Conversation.objects.get_or_create(
                workspace=creator_ws,
                contact=contact,
                defaults={'status': 'OPEN' if i % 2 == 0 else 'HANDOFF'}
            )
            Message.objects.create(
                conversation=conv,
                sender_type='CONTACT',
                content=f"Hey! Is the Wireless Headphones deal still active?"
            )
            Message.objects.create(
                conversation=conv,
                sender_type='BOT',
                content=f"Yes! Use coupon ALEX25 at checkout: https://socialflow.ai/@alex_creator"
            )

        # 9. Link Hub
        link_hub, _ = LinkHub.objects.get_or_create(
            creator=creator_user,
            defaults={
                'username': 'alex_creator',
                'title': 'Alex Rivers | Tech & Lifestyle Hub',
                'bio': 'Welcome! Shop my recommended gear, download guides, and claim exclusive discounts below.',
                'theme': 'PURPLE_GRADIENT',
                'total_views': 3420,
                'total_clicks': 1180
            }
        )
        LinkHubItem.objects.get_or_create(
            link_hub=link_hub,
            title="🎧 Acme Wireless Pro Headphones (25% OFF)",
            defaults={'item_type': 'PRODUCT', 'product': prod_headphone, 'position': 1, 'click_count': 450}
        )
        LinkHubItem.objects.get_or_create(
            link_hub=link_hub,
            title="📘 Download 2026 Monetization Playbook (PDF)",
            defaults={'item_type': 'DIGITAL_PRODUCT', 'product': prod_digital, 'position': 2, 'click_count': 320}
        )
        LinkHubItem.objects.get_or_create(
            link_hub=link_hub,
            title="📷 My Amazon Camera Gear List",
            defaults={'item_type': 'AFFILIATE_LINK', 'url': aff_link.url, 'position': 3, 'click_count': 410}
        )

        # 10. Promotions Marketplace & Deals
        promo, _ = Promotion.objects.get_or_create(
            brand=brand_user,
            title="Summer Tech Showcase 2026",
            defaults={
                'description': "Promote Acme's new wireless studio audio gear in your IG Reels & Stories. Looking for tech, gaming, and lifestyle creators.",
                'category': 'Tech & Electronics',
                'budget': 2500.00,
                'min_followers': 10000,
                'compensation_type': 'HYBRID',
                'start_date': timezone.now().date(),
                'end_date': (timezone.now() + timedelta(days=45)).date(),
                'status': 'PUBLISHED'
            }
        )
        PromotionInterest.objects.get_or_create(promotion=promo, creator=creator_user)
        PromotionApplication.objects.get_or_create(
            promotion=promo,
            creator=creator_user,
            defaults={
                'pitch': "I have 150k followers with an audience that loves audio gear! I will create 1 dedicated Reel and 3 Stories.",
                'requested_amount': 2200.00,
                'status': 'ACCEPTED'
            }
        )
        BrandDeal.objects.get_or_create(
            brand=brand_user,
            creator=creator_user,
            promotion=promo,
            defaults={
                'agreed_amount': 2200.00,
                'status': 'ACCEPTED',
                'deliverable_urls': 'https://instagram.com/p/mock_reel_123'
            }
        )

        # 11. Orders & Revenue Events
        for k in range(1, 10):
            order = Order.objects.create(
                workspace=creator_ws,
                order_number=f"SF-2026-{1000+k}",
                customer_name=f"Buyer {k}",
                customer_email=f"buyer{k}@domain.com",
                total_amount=149.99,
                status='DELIVERED',
                creator=creator_user,
                source='INSTAGRAM_AUTOMATION'
            )
            OrderItem.objects.create(
                order=order,
                product=prod_headphone,
                quantity=1,
                unit_price=149.99,
                total_price=149.99
            )
            RevenueEvent.objects.create(
                order=order,
                creator=creator_user,
                brand=brand_user,
                amount=149.99,
                commission_amount=15.00,
                attributed_source='COMMENT_TO_DM'
            )

        # 12. Audit Logs
        log_audit_event(actor=admin_user, action='SYSTEM_DEMO_SEEDED', details={'status': 'complete'})

        self.stdout.write(self.style.SUCCESS("Successfully populated real production database seed for SocialFlow AI!"))
