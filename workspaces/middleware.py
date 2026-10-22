from .models import Workspace

class WorkspaceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.workspace = None
        if request.user.is_authenticated:
            # First try owned workspace
            workspace = Workspace.objects.filter(owner=request.user, is_active=True).first()
            if not workspace:
                # Try membership
                membership = request.user.workspace_memberships.select_related('workspace').filter(workspace__is_active=True).first()
                if membership:
                    workspace = membership.workspace

            # If no workspace exists yet for this user (e.g. newly signed up), auto-create one
            if not workspace and not request.user.is_platform_admin:
                ws_type = 'CREATOR' if request.user.is_creator else 'BRAND'
                name = f"{request.user.username}'s Workspace"
                slug = f"{request.user.username.lower()}-workspace"
                count = Workspace.objects.filter(slug=slug).count()
                if count > 0:
                    slug = f"{slug}-{count+1}"
                workspace = Workspace.objects.create(
                    name=name,
                    slug=slug,
                    owner=request.user,
                    workspace_type=ws_type
                )
            request.workspace = workspace

        return self.get_response(request)
