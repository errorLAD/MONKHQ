from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, FileResponse, Http404, JsonResponse
from django.utils import timezone
from django.db import models
from .models import LinkHub, LinkHubItem, LinkClick, LinkView, LinkShortener, Subscriber, QRCode
from products.models import DigitalProduct, Product

try:
    from engagement.models import Contact, Lead
except ImportError:
    Contact, Lead = None, None

def parse_user_agent(user_agent_str):
    ua = user_agent_str.lower()
    device = "Mobile" if ("mobile" in ua or "android" in ua or "iphone" in ua) else ("Tablet" if "ipad" in ua else "Desktop")
    browser = "Chrome" if "chrome" in ua else ("Safari" if "safari" in ua else ("Firefox" if "firefox" in ua else ("Edge" if "edg" in ua else "Other")))
    os = "iOS" if ("iphone" in ua or "ipad" in ua) else ("Android" if "android" in ua else ("Windows" if "windows" in ua else ("Mac" if "macintosh" in ua else "Linux")))
    return device, browser, os

def public_linkhub_view(request, username):
    # Clean @ prefix if passed in path
    clean_username = username.lstrip('@')
    link_hub = get_object_or_404(LinkHub, username__iexact=clean_username, is_published=True)
    
    # Analytics Logging
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    ip_address = request.META.get('REMOTE_ADDR')
    referrer = request.META.get('HTTP_REFERER', '')
    device, browser, os = parse_user_agent(user_agent)
    
    # Determine traffic source
    ref_lower = referrer.lower()
    if 'instagram' in ref_lower:
        source = 'INSTAGRAM'
    elif 'youtube' in ref_lower:
        source = 'YOUTUBE'
    elif 'facebook' in ref_lower:
        source = 'FACEBOOK'
    elif 'tiktok' in ref_lower:
        source = 'TIKTOK'
    elif 'twitter' in ref_lower or 'x.com' in ref_lower:
        source = 'X'
    elif request.GET.get('source') == 'qr' or 'qr' in ref_lower:
        source = 'QR_CODE'
    else:
        source = 'DIRECT' if not referrer else 'OTHER'
        
    LinkView.objects.create(
        link_hub=link_hub,
        ip_address=ip_address,
        user_agent=user_agent,
        referrer=referrer,
        device_type=device,
        browser=browser,
        os=os,
        source=source,
        utm_source=request.GET.get('utm_source', ''),
        utm_medium=request.GET.get('utm_medium', ''),
        utm_campaign=request.GET.get('utm_campaign', ''),
        utm_content=request.GET.get('utm_content', ''),
        utm_term=request.GET.get('utm_term', ''),
    )
    
    LinkHub.objects.filter(id=link_hub.id).update(total_views=models.F('total_views') + 1)
    link_hub.refresh_from_db()
    
    # Fetch active items & filter out scheduled expired ones
    raw_items = link_hub.items.filter(is_active=True).order_by('position')
    now = timezone.now()
    items = []
    for item in raw_items:
        if item.start_time and now < item.start_time:
            continue
        if item.end_time and now > item.end_time:
            continue
        items.append(item)
        
    context = {
        'link_hub': link_hub,
        'items': items,
        'has_store_items': any(i.item_type in ['PRODUCT', 'DIGITAL_PRODUCT', 'AFFILIATE_PRODUCT'] for i in items),
    }
    return render(request, 'linkhub/public_profile.html', context)

def click_link_view(request, item_id):
    item = get_object_or_404(LinkHubItem, id=item_id)
    
    LinkHubItem.objects.filter(id=item.id).update(click_count=models.F('click_count') + 1)
    LinkHub.objects.filter(id=item.link_hub.id).update(total_clicks=models.F('total_clicks') + 1)
    
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    ip_address = request.META.get('REMOTE_ADDR')
    referrer = request.META.get('HTTP_REFERER', '')
    device, browser, os = parse_user_agent(user_agent)
    
    LinkClick.objects.create(
        link_hub_item=item,
        ip_address=ip_address,
        user_agent=user_agent,
        referrer=referrer,
        device_type=device,
        browser=browser,
        os=os,
        utm_source=request.GET.get('utm_source', ''),
        utm_medium=request.GET.get('utm_medium', ''),
        utm_campaign=request.GET.get('utm_campaign', '')
    )
    
    target_url = item.url
    if item.product and item.product.external_url:
        target_url = item.product.external_url
    elif item.product and item.product.affiliate_url:
        target_url = item.product.affiliate_url
        
    if not target_url or target_url.strip() in ['', '#', '/']:
        target_url = f"/@{item.link_hub.username}/"
        
    return redirect(target_url)

def short_link_redirect_view(request, slug):
    short_link = get_object_or_404(LinkShortener, slug=slug, is_active=True)
    if short_link.expiration and timezone.now() > short_link.expiration:
        raise Http404("Short link has expired.")
        
    LinkShortener.objects.filter(id=short_link.id).update(click_count=models.F('click_count') + 1)
    return redirect(short_link.target_url)

def digital_download_view(request, digital_id):
    digital = get_object_or_404(DigitalProduct, id=digital_id)
    DigitalProduct.objects.filter(id=digital.id).update(download_count=models.F('download_count') + 1)
    
    if digital.file:
        return FileResponse(digital.file.open(), as_attachment=True, filename=f"{digital.product.slug if hasattr(digital, 'product') and digital.product else 'download'}.pdf")
    else:
        content = f"MonkHQ Signed Content Access\nProduct: {digital.name if hasattr(digital, 'name') else 'Digital Item'}\nTimestamp: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\nThank you for your purchase!"
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="monkhq_digital_product.txt"'
        return response

def submit_lead_form_view(request, link_hub_id):
    if request.method == 'POST':
        link_hub = get_object_or_404(LinkHub, id=link_hub_id)
        name = request.POST.get('name', 'Anonymous Lead')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        message = request.POST.get('message', '')
        
        if email:
            Subscriber.objects.get_or_create(creator=link_hub.creator, email=email, defaults={'source': 'LINK_HUB_FORM'})
            if Contact and Lead:
                contact, _ = Contact.objects.get_or_create(
                    user=link_hub.creator if hasattr(Contact, 'user') else None,
                    email=email,
                    defaults={'name': name, 'phone': phone}
                )
                Lead.objects.create(
                    creator=link_hub.creator,
                    name=name,
                    email=email,
                    phone=phone,
                    notes=message,
                    source='LINK_HUB'
                )
        return HttpResponse('<div class="p-4 bg-emerald-50 text-emerald-700 font-bold text-sm rounded-xl text-center border border-emerald-200">✓ Thank you! Your message has been sent successfully.</div>')
    return JsonResponse({'error': 'Invalid request'}, status=400)

def subscribe_email_view(request, link_hub_id):
    if request.method == 'POST':
        link_hub = get_object_or_404(LinkHub, id=link_hub_id)
        email = request.POST.get('email', '').strip()
        if email:
            Subscriber.objects.get_or_create(creator=link_hub.creator, email=email, defaults={'source': 'LINK_HUB_SUBSCRIBE'})
            return HttpResponse('<div class="p-3 bg-emerald-500 text-white font-bold text-xs rounded-xl text-center animate-fade-in">✓ Subscribed successfully!</div>')
    return JsonResponse({'error': 'Invalid email'}, status=400)
