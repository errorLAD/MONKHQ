from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, Role
from workspaces.models import Workspace
from audit.models import AuditLog

class RoleAuthorizationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.creator = User.objects.create_user(username='test_creator', password='password123', role=Role.CREATOR)
        self.brand = User.objects.create_user(username='test_brand', password='password123', role=Role.BRAND)
        self.admin = User.objects.create_user(username='test_admin', password='password123', role=Role.PLATFORM_ADMIN, is_staff=True, is_superuser=True)

        self.creator_ws = Workspace.objects.create(name="Creator WS", owner=self.creator, slug="creator-ws")
        self.brand_ws = Workspace.objects.create(name="Brand WS", owner=self.brand, slug="brand-ws")

    def test_creator_access_creator_dashboard(self):
        self.client.login(username='test_creator', password='password123')
        response = self.client.get(reverse('creator_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_creator_cannot_access_brand_dashboard(self):
        self.client.login(username='test_creator', password='password123')
        response = self.client.get(reverse('brand_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_brand_cannot_access_creator_dashboard(self):
        self.client.login(username='test_brand', password='password123')
        response = self.client.get(reverse('creator_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_normal_user_cannot_access_admin_platform(self):
        self.client.login(username='test_creator', password='password123')
        response = self.client.get(reverse('admin_platform_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_admin_can_access_admin_platform(self):
        self.client.login(username='test_admin', password='password123')
        response = self.client.get(reverse('admin_platform_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_all_endpoints(self):
        self.client.login(username='test_admin', password='password123')
        endpoints = [
            'admin_platform_dashboard',
            'admin_platform_search',
            'admin_platform_users',
            'admin_platform_creators',
            'admin_platform_brands',
            'admin_platform_workspaces',
            'admin_platform_automations',
            'admin_platform_ai_engine',
            'admin_platform_engagement',
            'admin_platform_promotions',
            'admin_platform_linkhub',
            'admin_platform_products',
            'admin_platform_orders',
            'admin_platform_campaigns',
            'admin_platform_social',
            'admin_platform_subscriptions',
            'admin_platform_analytics',
            'admin_platform_developer',
            'admin_platform_health',
            'admin_platform_security',
            'admin_platform_audit_logs',
            'admin_platform_settings',
        ]
        for ep in endpoints:
            response = self.client.get(reverse(ep))
            self.assertEqual(response.status_code, 200, f"Endpoint {ep} failed with status {response.status_code}")

    def test_admin_user_ban_action(self):
        self.client.login(username='test_admin', password='password123')
        response = self.client.post(reverse('admin_platform_users'), {
            'user_id': str(self.creator.id),
            'action': 'ban',
            'reason': 'Test ban'
        })
        self.assertEqual(response.status_code, 302)
        self.creator.refresh_from_db()
        self.assertFalse(self.creator.is_active)
        self.assertTrue(AuditLog.objects.filter(action='USER_BANNED').exists())

    def test_admin_csv_export(self):
        self.client.login(username='test_admin', password='password123')
        response = self.client.get(reverse('admin_export_csv') + '?type=users')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_admin_impersonation(self):
        self.client.login(username='test_admin', password='password123')
        response = self.client.get(reverse('admin_impersonate', kwargs={'user_id': self.creator.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(AuditLog.objects.filter(action='ADMIN_IMPERSONATION_STARTED').exists())
