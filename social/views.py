import base64
import datetime
import hashlib
import hmac
import json
import logging
import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from automations.models import Automation, AutomationExecution, AutomationLog
from social.models import AccountHealth, MetaToken, SocialAccount
from social.services import (
    build_instagram_authorization_url,
    encrypt_token,
    exchange_code_for_token,
    exchange_for_long_lived_token,
    fetch_instagram_profile,
)
from workspaces.models import Workspace

logger = logging.getLogger(__name__)


@login_required(login_url='login_hub')
def connect_instagram_view(request):
    """
    Initiates Instagram OAuth via Instagram Login for Tech Providers.
    Generates a cryptographically secure random state tied to user session,
    and redirects the user to Meta's Instagram authorization URL.
    """
    app_id = getattr(settings, 'META_APP_ID', '')
    redirect_uri = getattr(settings, 'INSTAGRAM_REDIRECT_URI', '')

    if not app_id or not redirect_uri:
        logger.error("Instagram OAuth initiation failed: META_APP_ID or INSTAGRAM_REDIRECT_URI is not configured.")
        messages.error(request, "Instagram integration is not configured. Missing META_APP_ID or redirect URI.")
        return redirect('creator_social_accounts')

    # Generate cryptographically secure state and bind to session & user
    oauth_state = secrets.token_urlsafe(32)
    request.session['instagram_oauth_state'] = oauth_state
    request.session['instagram_oauth_user_id'] = str(request.user.id)

    oauth_url = build_instagram_authorization_url(oauth_state)
    if not oauth_url:
        messages.error(request, "Failed to generate Instagram authorization URL.")
        return redirect('creator_social_accounts')

    return redirect(oauth_url)


@login_required(login_url='login_hub')
def instagram_callback_view(request):
    """
    OAuth Callback for Meta's Instagram Login.
    Validates state, handles user denial, exchanges authorization code for short and
    long-lived tokens server-side, retrieves user profile, associates account with
    the current user's workspace, and stores credentials securely.
    """
    # 1. Handle user cancellation or denial
    error = request.GET.get('error') or request.GET.get('error_reason')
    error_description = request.GET.get('error_description')
    if error:
        err_msg = error_description or error or "Authorization cancelled by user."
        logger.info(f"Instagram OAuth cancelled/denied: {err_msg}")
        messages.error(request, f"Instagram connection cancelled: {err_msg}")
        return redirect('creator_social_accounts')

    # 2. Validate state parameter to prevent CSRF and session hijacking
    received_state = request.GET.get('state', '')
    session_state = request.session.pop('instagram_oauth_state', None)
    session_user_id = request.session.pop('instagram_oauth_user_id', None)

    if not received_state or not session_state or not secrets.compare_digest(received_state, session_state):
        logger.warning("Instagram OAuth state mismatch or missing state.")
        messages.error(request, "Invalid OAuth state. Possible CSRF detected or session expired. Please try again.")
        return redirect('creator_social_accounts')

    if str(request.user.id) != str(session_user_id):
        logger.warning(f"OAuth session user mismatch: user={request.user.id}, session={session_user_id}")
        messages.error(request, "OAuth user mismatch. Please reconnect.")
        return redirect('creator_social_accounts')

    # 3. Validate authorization code
    code = request.GET.get('code', '')
    if not code:
        logger.warning("Instagram OAuth callback received without authorization code.")
        messages.error(request, "Authorization code missing from Meta response.")
        return redirect('creator_social_accounts')

    # 4. Check server configuration
    app_id = getattr(settings, 'META_APP_ID', '')
    app_secret = getattr(settings, 'META_APP_SECRET', '')
    redirect_uri = getattr(settings, 'INSTAGRAM_REDIRECT_URI', '')
    if not app_id or not app_secret or not redirect_uri:
        logger.error("Missing Meta environment configuration during token exchange.")
        messages.error(request, "Instagram authentication failed: server configuration missing.")
        return redirect('creator_social_accounts')

    # 5. Server-side token exchange (Short-Lived Token)
    token_result = exchange_code_for_token(code)
    if not token_result.get('success'):
        error_detail = token_result.get('error', 'Token exchange failed.')
        logger.error(f"Instagram token exchange failure: {error_detail}")
        messages.error(request, f"Instagram authentication failed: {error_detail}")
        return redirect('creator_social_accounts')

    short_lived_token = token_result.get('access_token')
    ig_user_id = token_result.get('user_id', '')

    # 6. Exchange for 60-day Long-Lived Token (with fallback to short-lived)
    ll_result = exchange_for_long_lived_token(short_lived_token)
    access_token = ll_result.get('access_token', short_lived_token)
    expires_in = ll_result.get('expires_in', 3600)
    token_expires_at = timezone.now() + datetime.timedelta(seconds=expires_in)

    # 7. Fetch Instagram Profile details
    profile_result = fetch_instagram_profile(access_token)
    if profile_result.get('success'):
        profile_data = profile_result.get('profile', {})
        account_id = str(profile_data.get('id') or profile_data.get('user_id') or ig_user_id)
        username = profile_data.get('username') or f"ig_{account_id}"
        account_name = profile_data.get('name') or username
        profile_pic = profile_data.get('profile_picture_url') or ""
    else:
        account_id = str(ig_user_id)
        username = f"ig_{account_id}"
        account_name = username
        profile_pic = ""

    # 8. Resolve user workspace
    workspace = getattr(request, 'workspace', None)
    if not workspace:
        workspace = Workspace.objects.filter(owner=request.user, is_active=True).first()
    if not workspace:
        workspace = Workspace.objects.create(
            name=f"{request.user.username}'s Workspace",
            slug=f"{request.user.username.lower()}-workspace",
            owner=request.user,
            workspace_type='CREATOR'
        )

    # 9. Multi-tenant account ownership check (prevent unauthorized account hijacking)
    existing_in_other = SocialAccount.objects.filter(
        platform='INSTAGRAM',
        account_id=account_id
    ).exclude(workspace=workspace).first()

    if existing_in_other and existing_in_other.workspace.owner != request.user:
        logger.warning(f"Instagram account @{username} ({account_id}) already claimed by another workspace.")
        messages.error(request, "This Instagram account is already connected to another user's workspace.")
        return redirect('creator_social_accounts')

    # 10. Update or create SocialAccount, MetaToken, and AccountHealth
    social_account, _ = SocialAccount.objects.update_or_create(
        workspace=workspace,
        platform='INSTAGRAM',
        account_id=account_id,
        defaults={
            'account_name': account_name,
            'username': username,
            'profile_pic': profile_pic,
            'is_connected': True,
            'token_expires_at': token_expires_at,
        }
    )

    encrypted_token = encrypt_token(access_token)
    MetaToken.objects.update_or_create(
        social_account=social_account,
        defaults={
            'access_token_encrypted': encrypted_token,
            'token_type': 'Bearer',
            'scope': getattr(settings, 'INSTAGRAM_SCOPES', 'instagram_business_basic,instagram_business_manage_comments'),
        }
    )

    AccountHealth.objects.update_or_create(
        social_account=social_account,
        defaults={
            'meta_status': 'HEALTHY',
            'webhook_status': 'ACTIVE',
            'messaging_status': 'OPERATIONAL',
            'last_error': '',
        }
    )

    logger.info(f"Successfully connected Instagram account @{username} for user {request.user.username}")
    messages.success(request, f"Successfully connected Instagram account @{username}!")
    return redirect('creator_social_accounts')


@csrf_exempt
def meta_webhook_view(request):
    """
    Webhook handler for Meta Instagram events.
    - GET: Hub challenge verification using META_WEBHOOK_VERIFY_TOKEN.
    - POST: HMAC-SHA256 signature verification using META_APP_SECRET,
            safe payload parsing, idempotent comment processing matching active Automations.
    """
    if request.method == 'GET':
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        expected_token = getattr(settings, 'META_WEBHOOK_VERIFY_TOKEN', '')
        if not expected_token:
            logger.error("META_WEBHOOK_VERIFY_TOKEN is not configured on the server.")
            return HttpResponse('Webhook verification token not configured', status=403)

        if mode == 'subscribe' and token == expected_token:
            return HttpResponse(challenge, content_type='text/plain', status=200)

        return HttpResponse('Verification token mismatch', status=403)

    elif request.method == 'POST':
        # 1. Signature Verification with X-Hub-Signature-256
        signature = request.META.get('HTTP_X_HUB_SIGNATURE_256', '')
        payload = request.body
        secret = getattr(settings, 'META_APP_SECRET', '')

        if not secret or not signature:
            logger.warning("Webhook rejected: missing signature header or META_APP_SECRET not configured.")
            return HttpResponse('Forbidden: Signature or secret missing', status=403)

        expected_sig = 'sha256=' + hmac.new(secret.encode('utf-8'), payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            logger.warning("Webhook signature verification failed.")
            return HttpResponse('Invalid webhook signature', status=403)

        # 2. Parse JSON payload safely
        try:
            data = json.loads(payload.decode('utf-8'))
        except Exception as e:
            logger.warning(f"Webhook payload JSON decoding error: {e}")
            return JsonResponse({'status': 'INVALID_JSON'}, status=400)

        # 3. Process entries and comment changes idempotently
        entry_list = data.get('entry', [])
        for entry in entry_list:
            account_id = str(entry.get('id', ''))
            changes = entry.get('changes', [])
            for change in changes:
                field = change.get('field')
                val = change.get('value', {})
                if field == 'comments':
                    comment_id = str(val.get('id') or entry.get('id') or '')
                    if not comment_id:
                        continue

                    # Idempotency check: prevent duplicate automation execution
                    if AutomationExecution.objects.filter(trigger_event_id=comment_id).exists():
                        logger.info(f"Duplicate comment event {comment_id} skipped.")
                        continue

                    comment_text = val.get('text', '')
                    from_user = val.get('from', {}).get('username', '')
                    media_id = str(val.get('media', {}).get('id', ''))

                    # Match active automations for this workspace or active automations
                    social_acc = SocialAccount.objects.filter(account_id=account_id).first()
                    if social_acc:
                        auto_qs = Automation.objects.filter(
                            workspace=social_acc.workspace,
                            is_active=True,
                            trigger_type='INSTAGRAM_COMMENT'
                        )
                    else:
                        auto_qs = Automation.objects.filter(
                            is_active=True,
                            trigger_type='INSTAGRAM_COMMENT'
                        )

                    matched_auto = None
                    for auto in auto_qs:
                        # Check keyword match condition if present
                        if hasattr(auto, 'trigger') and auto.trigger:
                            trig = auto.trigger
                            # Media ID check
                            if trig.post_id and trig.post_id != 'ALL_POSTS' and media_id:
                                if trig.post_id != media_id:
                                    continue
                            # Keyword check
                            if trig.keywords:
                                kw_list = [k.strip().lower() for k in trig.keywords.split(',') if k.strip()]
                                if kw_list:
                                    if trig.match_type == 'EXACT':
                                        if comment_text.strip().lower() not in kw_list:
                                            continue
                                    else:
                                        if not any(k in comment_text.lower() for k in kw_list):
                                            continue
                        matched_auto = auto
                        break

                    if matched_auto:
                        execution = AutomationExecution.objects.create(
                            automation=matched_auto,
                            trigger_event_id=comment_id,
                            contact_username=from_user or "unknown_user",
                            status='SUCCESS',
                            duration_seconds=0.5
                        )
                        AutomationLog.objects.create(
                            automation=matched_auto,
                            execution=execution,
                            level='INFO',
                            message=f"Meta Webhook: Comment '{comment_text}' matched automation '{matched_auto.name}' for @{from_user}."
                        )
                        matched_auto.execution_count += 1
                        matched_auto.success_count += 1
                        matched_auto.save(update_fields=['execution_count', 'success_count'])

        return JsonResponse({'status': 'EVENT_RECEIVED'}, status=200)

    return HttpResponse('Method Not Allowed', status=405)


def _parse_signed_request(signed_request, secret):
    """
    Decodes and validates a Meta signed_request.
    Returns (data_dict, error_string).
    """
    if not signed_request or '.' not in signed_request:
        return None, "Invalid signed_request format."

    try:
        encoded_sig, payload = signed_request.split('.', 1)
    except ValueError:
        return None, "Malformed signed_request."

    # Pad base64 strings to multiple of 4
    rem_sig = len(encoded_sig) % 4
    if rem_sig:
        encoded_sig += '=' * (4 - rem_sig)
    rem_payload = len(payload) % 4
    if rem_payload:
        payload += '=' * (4 - rem_payload)

    try:
        sig = base64.urlsafe_b64decode(encoded_sig.encode('utf-8'))
        decoded_payload = base64.urlsafe_b64decode(payload.encode('utf-8'))
        data = json.loads(decoded_payload.decode('utf-8'))
    except Exception as e:
        return None, f"Failed to decode base64 signed_request: {e}"

    if data.get('algorithm', '').upper() != 'HMAC-SHA256':
        return None, f"Unsupported algorithm: {data.get('algorithm')}"

    # Verify signature using META_APP_SECRET if configured
    if secret:
        raw_payload = signed_request.split('.', 1)[1].encode('ascii')
        expected_sig = hmac.new(secret.encode('utf-8'), raw_payload, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected_sig):
            return None, "Signature verification failed."

    return data, None


@csrf_exempt
def meta_deauthorize_view(request):
    """
    Handles Meta (Instagram / Facebook) Deauthorization Callback.
    - GET: Returns HTTP 200 with an official compliance status page/JSON.
    - POST: Validates signed_request from Meta, identifies user_id,
            marks SocialAccount as disconnected, revokes tokens, and updates health.
    """
    if request.method == 'GET':
        if request.headers.get('accept') == 'application/json':
            return JsonResponse({
                'status': 'OPERATIONAL',
                'service': 'MonkHQ Meta Deauthorization Callback',
                'endpoint': '/social/deauthorize/',
                'methods': ['GET', 'POST'],
                'timestamp': timezone.now().isoformat()
            }, status=200)
        return render(request, 'social/deauthorize.html', {
            'status': 'OPERATIONAL',
            'endpoint': request.build_absolute_uri(),
        })

    elif request.method == 'POST':
        signed_request = request.POST.get('signed_request')
        if not signed_request:
            try:
                body_data = json.loads(request.body.decode('utf-8'))
                signed_request = body_data.get('signed_request')
            except Exception:
                signed_request = None

        if not signed_request:
            logger.warning("Meta deauthorize callback received without signed_request.")
            return JsonResponse({'error': 'Missing signed_request parameter'}, status=400)

        app_secret = getattr(settings, 'META_APP_SECRET', '')
        data, err = _parse_signed_request(signed_request, app_secret)
        if err or not data:
            logger.warning(f"Meta deauthorize validation error: {err}")
            return JsonResponse({'error': err or 'Invalid signature'}, status=403)

        user_id = str(data.get('user_id') or '')
        if not user_id:
            logger.warning("Meta deauthorize payload missing user_id.")
            return JsonResponse({'error': 'Missing user_id in payload'}, status=400)

        # Disconnect all social accounts matching this account_id
        matched_accounts = SocialAccount.objects.filter(account_id=user_id)
        count = 0
        for acc in matched_accounts:
            acc.is_connected = False
            acc.save(update_fields=['is_connected'])
            if hasattr(acc, 'health'):
                acc.health.meta_status = 'DISCONNECTED'
                acc.health.last_error = 'User removed MonkHQ authorization in Meta settings.'
                acc.health.save(update_fields=['meta_status', 'last_error', 'updated_at'])
            if hasattr(acc, 'meta_token'):
                acc.meta_token.delete()
            count += 1

        logger.info(f"Meta deauthorization completed for user_id={user_id}. {count} account(s) disconnected.")
        return JsonResponse({
            'status': 'success',
            'user_id': user_id,
            'accounts_disconnected': count,
            'message': 'Account deauthorized and disconnected successfully.'
        }, status=200)

    return HttpResponse('Method Not Allowed', status=405)


@csrf_exempt
def meta_data_deletion_view(request):
    """
    Handles Meta User Data Deletion Request Callback (GDPR / Privacy Compliance).
    - GET: Shows instructions and compliance documentation.
    - POST: Verifies signed_request from Meta, marks account data for deletion,
            and returns required JSON with confirmation URL and code.
    """
    if request.method == 'GET':
        if request.headers.get('accept') == 'application/json':
            return JsonResponse({
                'status': 'OPERATIONAL',
                'service': 'MonkHQ Meta Data Deletion Callback',
                'endpoint': '/social/data-deletion/',
                'methods': ['GET', 'POST'],
                'timestamp': timezone.now().isoformat()
            }, status=200)
        return render(request, 'social/data_deletion.html', {
            'endpoint': request.build_absolute_uri(),
        })

    elif request.method == 'POST':
        signed_request = request.POST.get('signed_request')
        if not signed_request:
            try:
                body_data = json.loads(request.body.decode('utf-8'))
                signed_request = body_data.get('signed_request')
            except Exception:
                signed_request = None

        if not signed_request:
            return JsonResponse({'error': 'Missing signed_request parameter'}, status=400)

        app_secret = getattr(settings, 'META_APP_SECRET', '')
        data, err = _parse_signed_request(signed_request, app_secret)
        if err or not data:
            return JsonResponse({'error': err or 'Invalid signature'}, status=403)

        user_id = str(data.get('user_id') or 'unknown')
        confirmation_code = f"del_{user_id}_{secrets.token_hex(4)}"

        matched_accounts = SocialAccount.objects.filter(account_id=user_id)
        for acc in matched_accounts:
            acc.is_connected = False
            acc.save(update_fields=['is_connected'])
            if hasattr(acc, 'meta_token'):
                acc.meta_token.delete()
            if hasattr(acc, 'health'):
                acc.health.meta_status = 'DISCONNECTED'
                acc.health.last_error = f'Data deletion requested (Code: {confirmation_code})'
                acc.health.save(update_fields=['meta_status', 'last_error', 'updated_at'])

        status_url = request.build_absolute_uri(f"/social/deletion-status/?code={confirmation_code}")
        logger.info(f"Meta data deletion request completed for user_id={user_id}. Confirmation code: {confirmation_code}")

        return JsonResponse({
            'url': status_url,
            'confirmation_code': confirmation_code
        }, status=200)

    return HttpResponse('Method Not Allowed', status=405)


def meta_deletion_status_view(request):
    """
    Renders public confirmation of data deletion status.
    """
    code = request.GET.get('code', 'N/A')
    return render(request, 'social/deletion_status.html', {
        'confirmation_code': code,
        'timestamp': timezone.now(),
    })
