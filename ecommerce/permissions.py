from .models import EcommerceUserPermissions


def get_ecommerce_user_permissions(user):
    """Get or create EcommerceUserPermissions for a user."""
    perms, created = EcommerceUserPermissions.objects.get_or_create(user=user)
    return perms
