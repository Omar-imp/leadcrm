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


def block_view_only(view_func):
    from functools import wraps
    from django.shortcuts import redirect
    from django.contrib import messages

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if (
            request.method == "POST"
            and request.user.is_authenticated
            and not request.user.is_superuser
        ):
            try:
                perms = request.user.custom_permissions

                path = request.path

                section = None

                if path.startswith('/projects/'):
                    section = 'projects'
                elif path.startswith('/quotations/'):
                    section = 'quotations'
                elif path.startswith('/companies/'):
                    section = 'contacts'
                elif path.startswith('/contacts/'):
                    section = 'contacts'
                elif path.startswith('/leads/'):
                    section = 'leads'

                if section and perms.is_view_only(section):
                    messages.error(
                        request,
                        f'You only have view access to {section}.'
                    )
                    return redirect('/')
            except Exception as e:
                print("BLOCK ERROR:", e)

        return view_func(request, *args, **kwargs)

    return wrapper