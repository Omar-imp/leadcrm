from django import template

register = template.Library()

@register.filter
def getattr_filter(obj, attr):
    """Allows {{ obj|getattr:attr }} in templates."""
    return getattr(obj, attr, 'none')

@register.filter(name='has_full_access')
def has_full_access(user, app_name):
    """Checks if the user has full access permissions for a specific app."""
    if not user or user.is_anonymous:
        return False
        
    # Grant immediate access to superusers
    if user.is_superuser:
        return True
        
    # Tailor this logic to match how you actually define full access in your CRM.
    # Example: checking a custom user profile attribute or Django permission system.
    return user.has_perm(f'{app_name}.full_access') or getattr(user, 'is_admin', False)
