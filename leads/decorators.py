from django.core.exceptions import PermissionDenied
from functools import wraps


def role_required(*roles):
    """
    Usage:
        @role_required('admin', 'sales_manager')
        def my_view(request): ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.shortcuts import redirect
                return redirect('login')
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            if not hasattr(request.user, 'profile'):
                raise PermissionDenied
            if request.user.profile.role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def admin_only(view_func):
    return role_required('admin')(view_func)


def sales_team(view_func):
    return role_required('admin', 'sales_manager', 'sales_executive')(view_func)


def managers_only(view_func):
    return role_required('admin', 'sales_manager', 'ceo')(view_func)