from .models import OrganizationMembership


def get_user_organization(user):
    """Returns the Organization for this user, or None if unassigned."""
    try:
        return user.org_membership.organization
    except OrganizationMembership.DoesNotExist:
        return None
    