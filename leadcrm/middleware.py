from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib import messages


class OrganizationAccessMiddleware:
    """
    Ensures a logged-in user can only access the CRM app(s) their
    Organization's product_type permits. Superusers bypass this check.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        path = request.path

        if user and user.is_authenticated and not user.is_superuser:
            from ecommerce.utils import get_user_organization
            org = get_user_organization(user)

            product_type = org.product_type if org else 'leads'

            if path.startswith('/ecommerce/') and product_type not in ('ecommerce', 'both'):
                logout(request)
                messages.error(request, "You don't have access to the E-commerce CRM.")
                return redirect('login_selector')

            if path.startswith('/leadcrm/') and product_type not in ('leads', 'both'):
                logout(request)
                messages.error(request, "You don't have access to the Lead CRM.")
                return redirect('login_selector')

        return self.get_response(request)
