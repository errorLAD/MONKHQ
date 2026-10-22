def user_role_context(request):
    if not request.user.is_authenticated:
        return {'current_role': None, 'workspace': getattr(request, 'workspace', None)}
    return {
        'current_role': request.user.role,
        'is_creator': request.user.is_creator,
        'is_brand': request.user.is_brand,
        'is_platform_admin': request.user.is_platform_admin,
        'workspace': getattr(request, 'workspace', None)
    }
