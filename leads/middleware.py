from django.shortcuts import render
from .permissions import is_path_allowed


class RoleAccessMiddleware:
    """
    Blocks access to URLs that don't belong to the logged-in user's role.
    Admins and superusers bypass this entirely.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user

        if user.is_authenticated and not user.is_superuser:
            role = getattr(getattr(user, 'profile', None), 'role', None)
            if role and role != 'admin':
                if not is_path_allowed(role, request.path):
                    return render(request, 'leads/403.html', status=403)

        return self.get_response(request)