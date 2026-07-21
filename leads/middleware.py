from django.shortcuts import render


class RoleAccessMiddleware:
    """
    Checks custom per-user permissions first.
    Falls back to role-based permissions if no custom permissions set.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user

        if user.is_authenticated and not user.is_superuser:
            role = getattr(getattr(user, 'profile', None), 'role', None)
            if role and role != 'admin':
                if not self._is_allowed(user, request.path):
                    return render(request, 'leads/403.html', status=403)

        return self.get_response(request)

    def _is_allowed(self, user, path):
        # always allow these
        if any(path.startswith(p) for p in [
            '/login', '/logout', '/admin', '/static', '/media', '/notifications'
        ]):
            return True

        # check custom permissions first
        try:
            perms = user.custom_permissions
            section = self._get_section(path)
            if section:
                return perms.has_access(section)
            return True
        except Exception:
            # fall back to role-based
            from .permissions import is_path_allowed
            role = getattr(getattr(user, 'profile', None), 'role', None)
            return is_path_allowed(role, path)

    def _get_section(self, path):
        mapping = {
            '/leads/': 'leads',
            '/contacts/': 'contacts',
            '/companies/': 'contacts',
            '/pipeline/': 'pipeline',
            '/opportunities/': 'pipeline',
            '/quotations/': 'quotations',
            '/projects/': 'projects',
            '/milestones/': 'projects',
            '/tasks/': 'tasks',
            '/meetings/': 'meetings',
            '/payments/': 'payments',
            '/followups/': 'followups',
            '/communications/': 'communications',
            '/tickets/': 'support',
            '/activity/': 'activity',
            '/reports/': 'reports',
            '/forecast/': 'reports',
            '/documents/': 'documents',
            '/contracts/': 'contracts',
            '/salespersons/': 'salespersons',
            '/users/': 'users',
            '/ceo/': 'ceo_dashboard',
            '/whatsapp/': 'whatsapp',
            '/emails/': 'emails',
            '/assistant/': None,
        }
        for prefix, section in mapping.items():
            if path.startswith(prefix):
                return section
        return None
    

    def is_view_only_request(user, path):
        """
        Returns True if this user has view-only access to this path.
        """
        try:
            perms = user.custom_permissions

            mapping = {
                '/leads/': 'leads',
                '/contacts/': 'contacts',
                '/companies/': 'contacts',
                '/pipeline/': 'pipeline',
                '/opportunities/': 'pipeline',
                '/quotations/': 'quotations',
                '/projects/': 'projects',
                '/milestones/': 'projects',
                '/tasks/': 'tasks',
                '/meetings/': 'meetings',
                '/payments/': 'payments',
                '/followups/': 'followups',
                '/communications/': 'communications',
                '/tickets/': 'support',
                '/activity/': 'activity',
                '/reports/': 'reports',
                '/forecast/': 'reports',
                '/documents/': 'documents',
                '/contracts/': 'contracts',
                '/salespersons/': 'salespersons',
                '/users/': 'users',
                '/ceo/': 'ceo_dashboard',
                '/whatsapp/': 'whatsapp',
            }

            section = None
            for prefix, sec in mapping.items():
                if path.startswith(prefix):
                    section = sec
                    break

            return section and perms.is_view_only(section)

        except Exception as e:
            print("VIEW ONLY ERROR:", e)
            return False