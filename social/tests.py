import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from automations.models import (
    Automation,
    AutomationExecution,
    AutomationLog,
    AutomationStatus,
    AutomationTrigger,
    TriggerType,
)
from social.models import AccountHealth, MetaToken, SocialAccount
from social.services import decrypt_token
from workspaces.models import Workspace

User = get_user_model()


class InstagramOAuthAndWebhookTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testcreator",
            email="creator@monkhq.in",
            password="SecurePassword123!",
            role="CREATOR"
        )
        self.workspace = Workspace.objects.create(
            name="Test Creator Workspace",
            slug="test-creator-workspace",
            owner=self.user,
            workspace_type="CREATOR"
        )

        self.other_user = User.objects.create_user(
            username="othercreator",
            email="other@monkhq.in",
            password="SecurePassword123!",
            role="CREATOR"
        )
        self.other_workspace = Workspace.objects.create(
            name="Other Creator Workspace",
            slug="other-creator-workspace",
            owner=self.other_user,
            workspace_type="CREATOR"
        )

    # -------------------------------------------------------------------------
    # 1. Login Initiation & Authentication Protection
    # -------------------------------------------------------------------------
    def test_connect_instagram_unauthenticated_redirects_to_login(self):
        """Unauthenticated requests to connect/instagram/ must redirect to login."""
        response = self.client.get(reverse('connect_instagram'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    @override_settings(
        META_APP_ID='meta_app_99999',
        INSTAGRAM_REDIRECT_URI='http://localhost:8000/social/callback/',
        INSTAGRAM_SCOPES='instagram_business_basic,instagram_business_manage_comments'
    )
    def test_connect_instagram_authenticated_generates_state_and_redirects(self):
        """Authenticated users should be redirected to Instagram OAuth dialog with valid state and scopes."""
        self.client.force_login(self.user)
        response = self.client.get(reverse('connect_instagram'))
        self.assertEqual(response.status_code, 302)

        redirect_url = response.url
        self.assertTrue(redirect_url.startswith('https://www.instagram.com/oauth/authorize'))

        parsed = urlparse(redirect_url)
        params = parse_qs(parsed.query)

        self.assertEqual(params.get('client_id'), ['meta_app_99999'])
        self.assertEqual(params.get('redirect_uri'), ['http://localhost:8000/social/callback/'])
        self.assertEqual(params.get('response_type'), ['code'])
        self.assertEqual(params.get('enable_fb_login'), ['0'])
        self.assertEqual(params.get('force_authentication'), ['1'])
        self.assertEqual(params.get('scope'), ['instagram_business_basic,instagram_business_manage_comments'])

        state = params.get('state')[0]
        self.assertTrue(bool(state))
        # Ensure state and user id were stored in session
        session = self.client.session
        self.assertEqual(session.get('instagram_oauth_state'), state)
        self.assertEqual(session.get('instagram_oauth_user_id'), str(self.user.id))

    # -------------------------------------------------------------------------
    # 2. Missing Environment Variables
    # -------------------------------------------------------------------------
    @override_settings(META_APP_ID='', INSTAGRAM_REDIRECT_URI='')
    def test_missing_env_variables_on_connect(self):
        """Missing credentials on connect should redirect safely with an error message."""
        self.client.force_login(self.user)
        response = self.client.get(reverse('connect_instagram'), follow=True)
        self.assertRedirects(response, reverse('creator_social_accounts'))
        messages = list(response.context.get('messages', []))
        self.assertTrue(any('not configured' in str(m) for m in messages))

    @override_settings(META_APP_ID='', META_APP_SECRET='', INSTAGRAM_REDIRECT_URI='')
    def test_missing_env_variables_on_callback(self):
        """Missing credentials on callback should redirect safely with an error message."""
        self.client.force_login(self.user)
        session = self.client.session
        session['instagram_oauth_state'] = 'valid_state_123'
        session['instagram_oauth_user_id'] = str(self.user.id)
        session.save()

        response = self.client.get(reverse('instagram_callback') + '?code=auth_code_xyz&state=valid_state_123', follow=True)
        self.assertRedirects(response, reverse('creator_social_accounts'))
        messages = list(response.context.get('messages', []))
        self.assertTrue(any('configuration missing' in str(m) for m in messages))

    # -------------------------------------------------------------------------
    # 3. User Denial and Missing Authorization Code
    # -------------------------------------------------------------------------
    def test_callback_user_denial(self):
        """User cancelling or denying authorization should redirect with appropriate message."""
        self.client.force_login(self.user)
        url = reverse('instagram_callback') + '?error=access_denied&error_reason=user_denied&error_description=Permissions+denied'
        response = self.client.get(url, follow=True)
        self.assertRedirects(response, reverse('creator_social_accounts'))
        messages = list(response.context.get('messages', []))
        self.assertTrue(any('cancelled' in str(m).lower() for m in messages))

    def test_callback_missing_code(self):
        """Callback missing authorization code should fail safely."""
        self.client.force_login(self.user)
        session = self.client.session
        session['instagram_oauth_state'] = 'state_without_code'
        session['instagram_oauth_user_id'] = str(self.user.id)
        session.save()

        response = self.client.get(reverse('instagram_callback') + '?state=state_without_code', follow=True)
        self.assertRedirects(response, reverse('creator_social_accounts'))
        messages = list(response.context.get('messages', []))
        self.assertTrue(any('missing' in str(m).lower() for m in messages))

    # -------------------------------------------------------------------------
    # 4. State Validation & CSRF / Session Tampering
    # -------------------------------------------------------------------------
    def test_callback_invalid_state_rejected(self):
        """State mismatch must be rejected to prevent CSRF."""
        self.client.force_login(self.user)
        session = self.client.session
        session['instagram_oauth_state'] = 'legitimate_state_token'
        session['instagram_oauth_user_id'] = str(self.user.id)
        session.save()

        response = self.client.get(reverse('instagram_callback') + '?code=some_code&state=tampered_state', follow=True)
        self.assertRedirects(response, reverse('creator_social_accounts'))
        messages = list(response.context.get('messages', []))
        self.assertTrue(any('invalid oauth state' in str(m).lower() for m in messages))

    def test_callback_user_session_mismatch_rejected(self):
        """If session user ID does not match authenticated user, abort."""
        self.client.force_login(self.user)
        session = self.client.session
        session['instagram_oauth_state'] = 'valid_state'
        session['instagram_oauth_user_id'] = str(self.other_user.id)  # Belongs to different user
        session.save()

        response = self.client.get(reverse('instagram_callback') + '?code=some_code&state=valid_state', follow=True)
        self.assertRedirects(response, reverse('creator_social_accounts'))
        messages = list(response.context.get('messages', []))
        self.assertTrue(any('user mismatch' in str(m).lower() for m in messages))

    # -------------------------------------------------------------------------
    # 5. Failed Token Exchange
    # -------------------------------------------------------------------------
    @override_settings(
        META_APP_ID='meta_app_99999',
        META_APP_SECRET='meta_sec_88888',
        INSTAGRAM_REDIRECT_URI='http://localhost:8000/social/callback/'
    )
    @patch('requests.post')
    def test_callback_failed_token_exchange(self, mock_post):
        """Handle 400/500 errors from Meta token endpoint gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'error_message': 'Code has expired or is invalid'
        }
        mock_post.return_value = mock_response

        self.client.force_login(self.user)
        session = self.client.session
        session['instagram_oauth_state'] = 'valid_state_456'
        session['instagram_oauth_user_id'] = str(self.user.id)
        session.save()

        response = self.client.get(reverse('instagram_callback') + '?code=expired_code&state=valid_state_456', follow=True)
        self.assertRedirects(response, reverse('creator_social_accounts'))
        messages = list(response.context.get('messages', []))
        self.assertTrue(any('failed' in str(m).lower() for m in messages))
        self.assertFalse(SocialAccount.objects.filter(workspace=self.workspace).exists())

    # -------------------------------------------------------------------------
    # 6. Successful OAuth Callback, Token Encryption, & Reconnection
    # -------------------------------------------------------------------------
    @override_settings(
        META_APP_ID='meta_app_99999',
        META_APP_SECRET='meta_sec_88888',
        INSTAGRAM_REDIRECT_URI='http://localhost:8000/social/callback/'
    )
    @patch('requests.get')
    @patch('requests.post')
    def test_callback_success_creates_account_and_encrypts_token(self, mock_post, mock_get):
        """Successful OAuth callback creates SocialAccount, encrypted MetaToken, and AccountHealth."""
        # Mock short-lived token POST
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {
            'access_token': 'IG_SHORT_LIVED_TOKEN_123',
            'user_id': '17841400123456789'
        }
        mock_post.return_value = mock_post_resp

        # Mock long-lived token exchange & profile GET
        def mock_get_side_effect(url, **kwargs):
            mock_r = MagicMock()
            mock_r.status_code = 200
            if 'access_token' in url and 'ig_exchange_token' in kwargs.get('params', {}).get('grant_type', ''):
                mock_r.json.return_value = {
                    'access_token': 'IG_LONG_LIVED_TOKEN_60DAYS_SECURE',
                    'token_type': 'bearer',
                    'expires_in': 5184000
                }
            elif 'me' in url:
                mock_r.json.return_value = {
                    'id': '17841400123456789',
                    'username': 'socialflow_star',
                    'name': 'SocialFlow Star Creator',
                    'account_type': 'BUSINESS',
                    'profile_picture_url': 'https://graph.instagram.com/pic.jpg'
                }
            return mock_r

        mock_get.side_effect = mock_get_side_effect

        self.client.force_login(self.user)
        session = self.client.session
        session['instagram_oauth_state'] = 'super_secure_state_777'
        session['instagram_oauth_user_id'] = str(self.user.id)
        session.save()

        response = self.client.get(
            reverse('instagram_callback') + '?code=valid_meta_auth_code&state=super_secure_state_777',
            follow=True
        )
        self.assertRedirects(response, reverse('creator_social_accounts'))

        # Verify SocialAccount was created for the correct workspace
        account = SocialAccount.objects.get(account_id='17841400123456789')
        self.assertEqual(account.workspace, self.workspace)
        self.assertEqual(account.username, 'socialflow_star')
        self.assertEqual(account.account_name, 'SocialFlow Star Creator')
        self.assertTrue(account.is_connected)
        self.assertIsNotNone(account.token_expires_at)

        # Verify MetaToken is encrypted and decrypts properly
        token_obj = MetaToken.objects.get(social_account=account)
        self.assertNotEqual(token_obj.access_token_encrypted, 'IG_LONG_LIVED_TOKEN_60DAYS_SECURE')
        decrypted = decrypt_token(token_obj.access_token_encrypted)
        self.assertEqual(decrypted, 'IG_LONG_LIVED_TOKEN_60DAYS_SECURE')

        # Verify AccountHealth
        health = AccountHealth.objects.get(social_account=account)
        self.assertEqual(health.meta_status, 'HEALTHY')
        self.assertEqual(health.webhook_status, 'ACTIVE')

        # Test Reconnection idempotency: Reconnecting updates the existing account rather than duplicating
        session = self.client.session
        session['instagram_oauth_state'] = 'reconnect_state_888'
        session['instagram_oauth_user_id'] = str(self.user.id)
        session.save()

        response2 = self.client.get(
            reverse('instagram_callback') + '?code=reconnect_code&state=reconnect_state_888',
            follow=True
        )
        self.assertRedirects(response2, reverse('creator_social_accounts'))
        self.assertEqual(SocialAccount.objects.filter(account_id='17841400123456789').count(), 1)

    # -------------------------------------------------------------------------
    # 7. Multi-Tenant Account Ownership & Cross-Workspace Hijack Prevention
    # -------------------------------------------------------------------------
    @override_settings(
        META_APP_ID='meta_app_99999',
        META_APP_SECRET='meta_sec_88888',
        INSTAGRAM_REDIRECT_URI='http://localhost:8000/social/callback/'
    )
    @patch('requests.get')
    @patch('requests.post')
    def test_unauthorized_cross_workspace_account_takeover_blocked(self, mock_post, mock_get):
        """A user cannot connect an Instagram account already claimed by a different user's workspace."""
        # Create existing account under user 1's workspace
        SocialAccount.objects.create(
            workspace=self.workspace,
            platform='INSTAGRAM',
            account_id='17841499999999999',
            username='user1_ig_account',
            account_name='User 1 IG'
        )

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {
            'access_token': 'IG_SHORT_TOKEN',
            'user_id': '17841499999999999'
        }
        mock_post.return_value = mock_post_resp

        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = {
            'id': '17841499999999999',
            'username': 'user1_ig_account',
        }
        mock_get.return_value = mock_get_resp

        # User 2 tries to connect the same account_id
        self.client.force_login(self.other_user)
        session = self.client.session
        session['instagram_oauth_state'] = 'state_user2'
        session['instagram_oauth_user_id'] = str(self.other_user.id)
        session.save()

        response = self.client.get(
            reverse('instagram_callback') + '?code=user2_code&state=state_user2',
            follow=True
        )
        self.assertRedirects(response, reverse('creator_social_accounts'))
        messages = list(response.context.get('messages', []))
        self.assertTrue(any('already connected to another' in str(m).lower() for m in messages))

        # Ensure account is still in User 1's workspace
        acc = SocialAccount.objects.get(account_id='17841499999999999')
        self.assertEqual(acc.workspace, self.workspace)

    # -------------------------------------------------------------------------
    # 8. Webhook GET Verification
    # -------------------------------------------------------------------------
    @override_settings(META_WEBHOOK_VERIFY_TOKEN='super_secret_verify_token_2026')
    def test_meta_webhook_verification_success(self):
        """GET with correct token and mode=subscribe returns challenge with status 200."""
        url = reverse('meta_webhook') + '?hub.mode=subscribe&hub.verify_token=super_secret_verify_token_2026&hub.challenge=CHALLENGE_CODE_12345'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode('utf-8'), 'CHALLENGE_CODE_12345')

    @override_settings(META_WEBHOOK_VERIFY_TOKEN='super_secret_verify_token_2026')
    def test_meta_webhook_verification_failures(self):
        """GET with wrong token or mode returns 403."""
        # Wrong token
        url_wrong_token = reverse('meta_webhook') + '?hub.mode=subscribe&hub.verify_token=WRONG_TOKEN&hub.challenge=CHALLENGE_123'
        response1 = self.client.get(url_wrong_token)
        self.assertEqual(response1.status_code, 403)

        # Wrong mode
        url_wrong_mode = reverse('meta_webhook') + '?hub.mode=unsubscribe&hub.verify_token=super_secret_verify_token_2026&hub.challenge=CHALLENGE_123'
        response2 = self.client.get(url_wrong_mode)
        self.assertEqual(response2.status_code, 403)

    @override_settings(META_WEBHOOK_VERIFY_TOKEN='')
    def test_meta_webhook_verification_unconfigured_token(self):
        """GET when META_WEBHOOK_VERIFY_TOKEN is missing returns 403."""
        url = reverse('meta_webhook') + '?hub.mode=subscribe&hub.verify_token=some_token&hub.challenge=CHALLENGE_123'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    # -------------------------------------------------------------------------
    # 9. Webhook POST Signature Verification (HMAC-SHA256)
    # -------------------------------------------------------------------------
    @override_settings(META_APP_SECRET='my_app_secret_signature_test')
    def test_meta_webhook_signature_failures(self):
        """Missing or tampered signatures should be rejected with HTTP 403."""
        payload = json.dumps({'object': 'instagram', 'entry': []})

        # Missing signature header
        resp1 = self.client.post(
            reverse('meta_webhook'),
            data=payload,
            content_type='application/json'
        )
        self.assertEqual(resp1.status_code, 403)

        # Invalid/tampered signature
        resp2 = self.client.post(
            reverse('meta_webhook'),
            data=payload,
            content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256='sha256=invalid_hash_signature_value'
        )
        self.assertEqual(resp2.status_code, 403)

    # -------------------------------------------------------------------------
    # 10. Valid Comment Webhook Payload & Idempotent Automation Execution
    # -------------------------------------------------------------------------
    @override_settings(META_APP_SECRET='my_app_secret_signature_test')
    def test_valid_comment_webhook_triggers_automation_idempotently(self):
        """Valid comment events match automations and process idempotently without duplication."""
        # Create connected SocialAccount
        social_acc = SocialAccount.objects.create(
            workspace=self.workspace,
            platform='INSTAGRAM',
            account_id='178414009999',
            username='my_creator_account'
        )

        # Create active comment automation
        auto = Automation.objects.create(
            workspace=self.workspace,
            creator=self.user,
            name="Comment to DM Automation",
            trigger_type=TriggerType.COMMENT,
            status=AutomationStatus.ACTIVE,
            is_active=True
        )
        AutomationTrigger.objects.create(
            automation=auto,
            event_type=TriggerType.COMMENT,
            keywords="PRICE, LINK",
            match_type="CONTAINS",
            post_id="ALL_POSTS"
        )

        webhook_data = {
            "object": "instagram",
            "entry": [
                {
                    "id": "178414009999",
                    "time": 1720000000,
                    "changes": [
                        {
                            "field": "comments",
                            "value": {
                                "id": "comment_event_unique_555",
                                "text": "What is the price of this course? Link please!",
                                "from": {
                                    "id": "customer_123",
                                    "username": "excited_buyer"
                                },
                                "media": {
                                    "id": "post_media_001"
                                }
                            }
                        }
                    ]
                }
            ]
        }
        payload_bytes = json.dumps(webhook_data).encode('utf-8')
        secret = 'my_app_secret_signature_test'
        sig = 'sha256=' + hmac.new(secret.encode('utf-8'), payload_bytes, hashlib.sha256).hexdigest()

        # Send first webhook delivery
        resp = self.client.post(
            reverse('meta_webhook'),
            data=payload_bytes,
            content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256=sig
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {'status': 'EVENT_RECEIVED'})

        # Verify AutomationExecution was created
        executions = AutomationExecution.objects.filter(trigger_event_id='comment_event_unique_555')
        self.assertEqual(executions.count(), 1)
        execution = executions.first()
        self.assertEqual(execution.automation, auto)
        self.assertEqual(execution.contact_username, 'excited_buyer')
        self.assertEqual(execution.status, 'SUCCESS')

        # Verify AutomationLog was created
        log = AutomationLog.objects.filter(execution=execution).first()
        self.assertIsNotNone(log)
        self.assertIn("excited_buyer", log.message)

        # Verify automation stats updated
        auto.refresh_from_db()
        self.assertEqual(auto.execution_count, 1)
        self.assertEqual(auto.success_count, 1)

        # Send duplicate webhook delivery with the exact same event ID
        resp2 = self.client.post(
            reverse('meta_webhook'),
            data=payload_bytes,
            content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256=sig
        )
        self.assertEqual(resp2.status_code, 200)

        # Ensure idempotency: count must still be 1 (no duplicate execution)
        self.assertEqual(AutomationExecution.objects.filter(trigger_event_id='comment_event_unique_555').count(), 1)
        auto.refresh_from_db()
        self.assertEqual(auto.execution_count, 1)

    @override_settings(META_APP_SECRET='my_app_secret_signature_test')
    def test_webhook_ignores_unsupported_fields_without_crashing(self):
        """Unsupported webhook events (like stories or likes) are ignored safely."""
        webhook_data = {
            "object": "instagram",
            "entry": [
                {
                    "id": "178414009999",
                    "time": 1720000000,
                    "changes": [
                        {
                            "field": "unsupported_field_event",
                            "value": {"dummy": "data"}
                        }
                    ]
                }
            ]
        }
        payload_bytes = json.dumps(webhook_data).encode('utf-8')
        sig = 'sha256=' + hmac.new('my_app_secret_signature_test'.encode('utf-8'), payload_bytes, hashlib.sha256).hexdigest()

        resp = self.client.post(
            reverse('meta_webhook'),
            data=payload_bytes,
            content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256=sig
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {'status': 'EVENT_RECEIVED'})
        self.assertEqual(AutomationExecution.objects.count(), 0)


class MetaDeauthorizeAndDataDeletionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="deauth_creator",
            email="deauth@monkhq.in",
            password="SecurePassword123!",
            role="CREATOR"
        )
        self.workspace = Workspace.objects.create(
            name="Deauth Workspace",
            slug="deauth-workspace",
            owner=self.user,
            workspace_type="CREATOR"
        )
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform='INSTAGRAM',
            account_id='meta_user_999888',
            account_name='Deauth Test IG',
            username='deauth_ig_test',
            is_connected=True
        )
        self.meta_token = MetaToken.objects.create(
            social_account=self.account,
            access_token_encrypted='encrypted_dummy_token'
        )
        self.health = AccountHealth.objects.create(
            social_account=self.account,
            meta_status='HEALTHY'
        )
        self.secret = 'test_meta_app_secret_321'

    def _create_signed_request(self, user_id, secret=None):
        import base64
        secret = secret or self.secret
        payload_data = {'algorithm': 'HMAC-SHA256', 'user_id': user_id, 'issued_at': 1700000000}
        payload_json = json.dumps(payload_data)
        encoded_payload = base64.urlsafe_b64encode(payload_json.encode('utf-8')).decode('utf-8').rstrip('=')
        sig = hmac.new(secret.encode('utf-8'), encoded_payload.encode('ascii'), hashlib.sha256).digest()
        encoded_sig = base64.urlsafe_b64encode(sig).decode('utf-8').rstrip('=')
        return f"{encoded_sig}.{encoded_payload}"

    def test_deauthorize_get_renders_200_ok(self):
        """GET /social/deauthorize/ renders 200 OK HTML for browser testers."""
        response = self.client.get(reverse('meta_deauthorize'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Deauthorization Callback")
        self.assertContains(response, "Endpoint Status: Healthy")

    def test_deauthorize_get_json_accept_header(self):
        """GET /social/deauthorize/ returns JSON when Accept: application/json."""
        response = self.client.get(reverse('meta_deauthorize'), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'OPERATIONAL')

    @override_settings(META_APP_SECRET='test_meta_app_secret_321')
    def test_deauthorize_post_valid_signed_request(self):
        """POST /social/deauthorize/ with valid signature disconnects account and revokes token."""
        signed_request = self._create_signed_request('meta_user_999888')
        response = self.client.post(
            reverse('meta_deauthorize'),
            data={'signed_request': signed_request}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['user_id'], 'meta_user_999888')
        self.assertEqual(data['accounts_disconnected'], 1)

        self.account.refresh_from_db()
        self.assertFalse(self.account.is_connected)
        self.health.refresh_from_db()
        self.assertEqual(self.health.meta_status, 'DISCONNECTED')
        self.assertFalse(MetaToken.objects.filter(social_account=self.account).exists())

    @override_settings(META_APP_SECRET='test_meta_app_secret_321')
    def test_deauthorize_post_invalid_signature_rejected(self):
        """POST /social/deauthorize/ with invalid signature returns 403."""
        signed_request = self._create_signed_request('meta_user_999888', secret='wrong_secret')
        response = self.client.post(
            reverse('meta_deauthorize'),
            data={'signed_request': signed_request}
        )
        self.assertEqual(response.status_code, 403)
        self.account.refresh_from_db()
        self.assertTrue(self.account.is_connected)

    def test_deauthorize_post_missing_signed_request(self):
        """POST /social/deauthorize/ without signed_request returns 400."""
        response = self.client.post(reverse('meta_deauthorize'), data={})
        self.assertEqual(response.status_code, 400)

    def test_data_deletion_get_renders_200_ok(self):
        """GET /social/data-deletion/ returns 200 OK instructions."""
        response = self.client.get(reverse('meta_data_deletion'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Data Deletion Request")

    @override_settings(META_APP_SECRET='test_meta_app_secret_321')
    def test_data_deletion_post_valid_returns_status_url_and_code(self):
        """POST /social/data-deletion/ returns required Meta URL and confirmation code."""
        signed_request = self._create_signed_request('meta_user_999888')
        response = self.client.post(
            reverse('meta_data_deletion'),
            data={'signed_request': signed_request}
        )
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertIn('url', json_data)
        self.assertIn('confirmation_code', json_data)
        self.assertTrue(json_data['confirmation_code'].startswith('del_meta_user_999888'))

    def test_deletion_status_get_renders_200_ok(self):
        """GET /social/deletion-status/ renders 200 OK."""
        response = self.client.get(reverse('meta_deletion_status') + '?code=del_123')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "del_123")


class InstagramContentPublishingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="publisher_creator",
            email="publisher@monkhq.in",
            password="SecurePassword123!",
            role="CREATOR"
        )
        self.workspace = Workspace.objects.create(
            name="Publisher Workspace",
            slug="publisher-workspace",
            owner=self.user,
            workspace_type="CREATOR"
        )
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform='INSTAGRAM',
            account_id='17841400112233',
            account_name='Publisher IG Test',
            username='publisher_ig',
            is_connected=True
        )
        from social.services import encrypt_token
        self.token = MetaToken.objects.create(
            social_account=self.account,
            access_token_encrypted=encrypt_token('EAABtest_valid_meta_token_12345'),
            token_type='Bearer'
        )

    def test_publish_unauthenticated_redirects(self):
        """Unauthenticated requests to publish page redirect to login."""
        resp = self.client.get(reverse('instagram_publish'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp.url)

    def test_publish_get_renders_composer(self):
        """Authenticated user sees Instagram publisher composer with connected account."""
        self.client.force_login(self.user)
        resp = self.client.get(reverse('instagram_publish'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Instagram Post Publisher")
        self.assertContains(resp, "@publisher_ig")
        self.assertContains(resp, "instagram_content_publish")

    def test_publish_post_rejects_non_https_media(self):
        """Publishing must reject non-HTTPS URLs as required by Meta."""
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse('instagram_publish'),
            data={
                'account_id': '17841400112233',
                'media_url': 'http://insecure.example.com/photo.jpg',
                'caption': 'Testing insecure link',
                'media_type': 'IMAGE'
            },
            follow=True
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Meta requires the media URL to use a secure HTTPS protocol.")
        from social.models import InstagramPost
        self.assertEqual(InstagramPost.objects.count(), 0)

    @patch('social.services.requests.post')
    @patch('social.services.requests.get')
    def test_publish_post_success_flow(self, mock_get, mock_post):
        """Full publishing flow calls Meta container + publish endpoints and stores record."""
        # Mock container creation (Step 1)
        mock_container_resp = MagicMock()
        mock_container_resp.status_code = 200
        mock_container_resp.json.return_value = {'id': '179998887770001'}

        # Mock media publish (Step 2)
        mock_publish_resp = MagicMock()
        mock_publish_resp.status_code = 200
        mock_publish_resp.json.return_value = {'id': '180009998881112'}

        mock_post.side_effect = [mock_container_resp, mock_publish_resp]

        # Mock permalink lookup
        mock_permalink_resp = MagicMock()
        mock_permalink_resp.status_code = 200
        mock_permalink_resp.json.return_value = {'permalink': 'https://www.instagram.com/p/TESTPOST123/'}
        mock_get.return_value = mock_permalink_resp

        self.client.force_login(self.user)
        resp = self.client.post(
            reverse('instagram_publish'),
            data={
                'account_id': '17841400112233',
                'media_url': 'https://images.unsplash.com/photo-1618005182384.jpg',
                'caption': 'Check out our new launch! Comment LINK for 20% off. #MonkHQ',
                'media_type': 'IMAGE'
            },
            follow=True
        )

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Successfully published post to @publisher_ig")

        from social.models import InstagramPost
        post = InstagramPost.objects.first()
        self.assertIsNotNone(post)
        self.assertEqual(post.status, 'PUBLISHED')
        self.assertEqual(post.instagram_media_id, '180009998881112')
        self.assertEqual(post.container_id, '179998887770001')
        self.assertEqual(post.permalink, 'https://www.instagram.com/p/TESTPOST123/')
        self.assertIsNotNone(post.published_at)

    def test_posts_list_view_returns_json(self):
        """GET /social/posts/ returns JSON list of published posts for workspace."""
        from social.models import InstagramPost
        InstagramPost.objects.create(
            workspace=self.workspace,
            social_account=self.account,
            media_type='IMAGE',
            caption='API post test',
            media_url='https://example.com/test.jpg',
            status='PUBLISHED',
            instagram_media_id='ig_999999'
        )
        self.client.force_login(self.user)
        resp = self.client.get(reverse('instagram_posts_list'))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('posts', data)
        self.assertEqual(len(data['posts']), 1)
        self.assertEqual(data['posts'][0]['instagram_media_id'], 'ig_999999')

    def test_privacy_policy_accessible_200_ok(self):
        """Privacy Policy must return 200 OK with compliance terms."""
        resp = self.client.get(reverse('privacy_policy'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Privacy Policy")
        self.assertContains(resp, "instagram_content_publish")

    def test_terms_of_service_accessible_200_ok(self):
        """Terms of Service must return 200 OK."""
        resp = self.client.get(reverse('terms_of_service'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Terms of Service")


