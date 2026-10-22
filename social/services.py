import base64
import hashlib
import logging
import requests
from urllib.parse import urlencode
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

def _get_fernet():
    secret = getattr(settings, 'SECRET_KEY', 'default_secret_key_2026')
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode('utf-8')).digest())
    return Fernet(key)

def encrypt_token(token: str) -> str:
    """Encrypt access tokens before storing in the database."""
    if not token:
        return ""
    try:
        cipher = _get_fernet()
        return cipher.encrypt(token.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger.error(f"Error encrypting token: {e}")
        return token

def decrypt_token(encrypted_token: str) -> str:
    """Decrypt access tokens retrieved from the database."""
    if not encrypted_token:
        return ""
    try:
        cipher = _get_fernet()
        return cipher.decrypt(encrypted_token.encode('utf-8')).decode('utf-8')
    except Exception:
        # If not encrypted or previously saved in plain text, return safely
        return encrypted_token

def build_instagram_authorization_url(state: str) -> str:
    """
    Constructs the authorization URL for Meta's Instagram API using Instagram Login.
    Endpoint: https://www.instagram.com/oauth/authorize
    """
    app_id = getattr(settings, 'META_APP_ID', '')
    redirect_uri = getattr(settings, 'INSTAGRAM_REDIRECT_URI', '')
    scopes = getattr(settings, 'INSTAGRAM_SCOPES', 'instagram_business_basic,instagram_business_manage_comments')

    if not app_id or not redirect_uri:
        return ""

    params = {
        'enable_fb_login': '0',
        'force_authentication': '1',
        'client_id': app_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': scopes,
        'state': state,
    }
    return f"https://www.instagram.com/oauth/authorize?{urlencode(params)}"

def exchange_code_for_token(code: str) -> dict:
    """
    Exchanges authorization code for short-lived access token server-side.
    Endpoint: POST https://api.instagram.com/oauth/access_token
    """
    app_id = getattr(settings, 'META_APP_ID', '')
    app_secret = getattr(settings, 'META_APP_SECRET', '')
    redirect_uri = getattr(settings, 'INSTAGRAM_REDIRECT_URI', '')

    if not app_id or not app_secret or not redirect_uri:
        return {
            'success': False,
            'error': 'Missing Meta configuration (META_APP_ID, META_APP_SECRET, or INSTAGRAM_REDIRECT_URI).'
        }

    clean_code = code.split('#_')[0] if code else ''
    token_url = "https://api.instagram.com/oauth/access_token"
    payload = {
        'client_id': app_id,
        'client_secret': app_secret,
        'grant_type': 'authorization_code',
        'redirect_uri': redirect_uri,
        'code': clean_code,
    }

    try:
        response = requests.post(token_url, data=payload, timeout=10)
        if response.status_code != 200:
            logger.warning(f"Instagram token exchange returned status {response.status_code}")
            try:
                err_data = response.json()
                err_msg = err_data.get('error_message') or err_data.get('error', {}).get('message') or "Token exchange failed."
            except Exception:
                err_msg = f"HTTP {response.status_code} from Instagram token endpoint."
            return {'success': False, 'error': err_msg}

        data = response.json()
        access_token = data.get('access_token')
        user_id = str(data.get('user_id', ''))
        if not access_token:
            return {'success': False, 'error': 'No access token returned in Meta response.'}

        return {
            'success': True,
            'access_token': access_token,
            'user_id': user_id,
        }
    except requests.RequestException as e:
        logger.error(f"Network error during Instagram token exchange: {e}")
        return {'success': False, 'error': 'Network error connecting to Instagram token endpoint.'}

def exchange_for_long_lived_token(short_lived_token: str) -> dict:
    """
    Exchanges a short-lived token for a 60-day long-lived access token.
    Endpoint: GET https://graph.instagram.com/access_token
    """
    app_secret = getattr(settings, 'META_APP_SECRET', '')
    if not app_secret or not short_lived_token:
        return {'success': False, 'access_token': short_lived_token, 'expires_in': 3600}

    url = "https://graph.instagram.com/access_token"
    params = {
        'grant_type': 'ig_exchange_token',
        'client_secret': app_secret,
        'access_token': short_lived_token,
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                'success': True,
                'access_token': data.get('access_token', short_lived_token),
                'expires_in': data.get('expires_in', 5184000),
                'token_type': data.get('token_type', 'bearer'),
            }
    except Exception as e:
        logger.warning(f"Could not exchange for long-lived token: {e}")

    return {'success': False, 'access_token': short_lived_token, 'expires_in': 3600}

def fetch_instagram_profile(access_token: str) -> dict:
    """
    Retrieves Instagram account identity fields using Graph API v21.0.
    Endpoint: GET https://graph.instagram.com/v21.0/me
    """
    if not access_token:
        return {'success': False, 'error': 'No access token provided.'}

    url = "https://graph.instagram.com/v21.0/me"
    params = {
        'fields': 'id,user_id,username,name,account_type,profile_picture_url',
        'access_token': access_token,
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return {'success': True, 'profile': response.json()}
        else:
            logger.warning(f"Instagram profile fetch returned status {response.status_code}")
            return {'success': False, 'error': f"HTTP {response.status_code} fetching Instagram profile."}
    except requests.RequestException as e:
        logger.error(f"Network error fetching Instagram profile: {e}")
        return {'success': False, 'error': 'Network error connecting to Instagram Graph API.'}


def create_instagram_media_container(social_account, media_url: str, caption: str = "", media_type: str = "IMAGE") -> dict:
    """
    Step 1 of Instagram Content Publishing API: Create an item container.
    Endpoint: POST https://graph.instagram.com/v21.0/{ig-user-id}/media
    """
    if not hasattr(social_account, 'meta_token') or not social_account.meta_token:
        return {'success': False, 'error': 'No Meta access token associated with this Instagram account.'}

    access_token = decrypt_token(social_account.meta_token.access_token_encrypted)
    if not access_token:
        return {'success': False, 'error': 'Failed to decrypt access token for Instagram account.'}

    account_id = str(social_account.account_id)
    url = f"https://graph.instagram.com/v21.0/{account_id}/media"

    payload = {
        'access_token': access_token,
        'caption': caption,
    }

    if media_type.upper() == 'REEL':
        payload['media_type'] = 'REELS'
        payload['video_url'] = media_url
    else:
        payload['image_url'] = media_url

    try:
        response = requests.post(url, data=payload, timeout=20)
        data = response.json()
        if response.status_code == 200 and 'id' in data:
            return {
                'success': True,
                'container_id': str(data['id']),
            }
        else:
            err = data.get('error', {}).get('message') or f"HTTP {response.status_code} creating media container."
            logger.warning(f"Instagram media container creation failed: {err}")
            return {'success': False, 'error': err}
    except requests.RequestException as e:
        logger.error(f"Network error creating Instagram media container: {e}")
        return {'success': False, 'error': f"Network error during media container creation: {e}"}


def publish_instagram_media_container(social_account, container_id: str) -> dict:
    """
    Step 2 of Instagram Content Publishing API: Publish the created container.
    Endpoint: POST https://graph.instagram.com/v21.0/{ig-user-id}/media_publish
    """
    if not hasattr(social_account, 'meta_token') or not social_account.meta_token:
        return {'success': False, 'error': 'No Meta access token associated with this Instagram account.'}

    access_token = decrypt_token(social_account.meta_token.access_token_encrypted)
    account_id = str(social_account.account_id)
    url = f"https://graph.instagram.com/v21.0/{account_id}/media_publish"

    payload = {
        'creation_id': container_id,
        'access_token': access_token,
    }

    try:
        response = requests.post(url, data=payload, timeout=25)
        data = response.json()
        if response.status_code == 200 and 'id' in data:
            return {
                'success': True,
                'media_id': str(data['id']),
            }
        else:
            err = data.get('error', {}).get('message') or f"HTTP {response.status_code} publishing media container."
            logger.warning(f"Instagram media publish failed: {err}")
            return {'success': False, 'error': err}
    except requests.RequestException as e:
        logger.error(f"Network error publishing Instagram media: {e}")
        return {'success': False, 'error': f"Network error during media publishing: {e}"}


def fetch_instagram_media_permalink(social_account, media_id: str) -> str:
    """
    Fetches the live public permalink for a published Instagram media item.
    """
    if not hasattr(social_account, 'meta_token') or not social_account.meta_token:
        return ""

    access_token = decrypt_token(social_account.meta_token.access_token_encrypted)
    url = f"https://graph.instagram.com/v21.0/{media_id}"
    params = {
        'fields': 'permalink',
        'access_token': access_token,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json().get('permalink', '')
    except Exception as e:
        logger.warning(f"Failed to fetch permalink for media {media_id}: {e}")
    return ""


def publish_to_instagram(social_account, media_url: str, caption: str = "", media_type: str = "IMAGE", workspace=None):
    """
    Complete flow to publish media to Instagram:
    1. Validates account connection and tokens.
    2. Records post in database.
    3. Creates Instagram Media Container.
    4. Publishes Media Container to Instagram feed.
    5. Updates post with live Instagram Media ID and permalink.
    """
    from social.models import InstagramPost

    target_workspace = workspace or social_account.workspace

    post_record = InstagramPost.objects.create(
        workspace=target_workspace,
        social_account=social_account,
        media_type=media_type.upper(),
        caption=caption,
        media_url=media_url,
        status='PUBLISHING'
    )

    if not social_account.is_connected:
        post_record.status = 'FAILED'
        post_record.error_message = "Instagram account is disconnected. Please reconnect your account."
        post_record.save(update_fields=['status', 'error_message'])
        return {'success': False, 'post': post_record, 'error': post_record.error_message}

    # Step 1: Create Container
    container_res = create_instagram_media_container(
        social_account=social_account,
        media_url=media_url,
        caption=caption,
        media_type=media_type
    )

    if not container_res.get('success'):
        post_record.status = 'FAILED'
        post_record.error_message = container_res.get('error', 'Failed to create Instagram container.')
        post_record.save(update_fields=['status', 'error_message'])
        return {'success': False, 'post': post_record, 'error': post_record.error_message}

    container_id = container_res['container_id']
    post_record.container_id = container_id
    post_record.status = 'CONTAINER_CREATED'
    post_record.save(update_fields=['container_id', 'status'])

    # Step 2: Publish Container
    publish_res = publish_instagram_media_container(
        social_account=social_account,
        container_id=container_id
    )

    if not publish_res.get('success'):
        post_record.status = 'FAILED'
        post_record.error_message = publish_res.get('error', 'Failed to publish Instagram media container.')
        post_record.save(update_fields=['status', 'error_message'])
        return {'success': False, 'post': post_record, 'error': post_record.error_message}

    media_id = publish_res['media_id']
    permalink = fetch_instagram_media_permalink(social_account, media_id)

    post_record.status = 'PUBLISHED'
    post_record.instagram_media_id = media_id
    post_record.permalink = permalink or f"https://www.instagram.com/p/{media_id}/"
    post_record.published_at = timezone.now()
    post_record.error_message = ""
    post_record.save(update_fields=['status', 'instagram_media_id', 'permalink', 'published_at', 'error_message'])

    return {
        'success': True,
        'post': post_record,
        'media_id': media_id,
        'permalink': post_record.permalink,
    }
