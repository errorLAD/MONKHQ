from django.shortcuts import redirect
from django.contrib import messages

class RoleAuthorizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Creator URL Protection
        if path.startswith('/creator/') and not path.startswith('/creator/login') and not path.startswith('/creator/signup'):
            if not request.user.is_authenticated:
                messages.error(request, 'Please log in to access the Creator portal.')
                return redirect('creator_login')
            if not (request.user.is_creator or request.user.is_superuser):
                messages.error(request, 'Access denied. You do not have Creator privileges.')
                return redirect('brand_dashboard' if request.user.is_brand else 'creator_login')

        # Brand URL Protection
        if path.startswith('/brand/') and not path.startswith('/brand/login') and not path.startswith('/brand/signup'):
            if not request.user.is_authenticated:
                messages.error(request, 'Please log in to access the Brand portal.')
                return redirect('brand_login')
            if not (request.user.is_brand or request.user.is_superuser):
                messages.error(request, 'Access denied. You do not have Brand privileges.')
                return redirect('creator_dashboard' if request.user.is_creator else 'brand_login')

        # Platform Admin Protection
        if path.startswith('/admin-platform/') and not path.startswith('/admin-platform/login'):
            if not request.user.is_authenticated:
                messages.error(request, 'Please log in to access Platform Admin.')
                return redirect('admin_platform_login')
            if not request.user.is_platform_admin:
                messages.error(request, 'Access denied. Platform Admin authorization required.')
                return redirect('creator_login')

        return self.get_response(request)
