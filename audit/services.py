from .models import AuditLog

def log_audit_event(actor=None, action="", resource_type="", resource_id="", request=None, details=None):
    ip_address = None
    user_agent = None
    actor_email = None

    if actor and hasattr(actor, 'email'):
        actor_email = actor.email or actor.username

    if request:
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            ip_address = x_forwarded.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT')
        if not actor and request.user.is_authenticated:
            actor = request.user
            actor_email = request.user.email or request.user.username

    return AuditLog.objects.create(
        actor=actor,
        actor_email=actor_email,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else "",
        ip_address=ip_address,
        user_agent=user_agent,
        details=details or {}
    )
