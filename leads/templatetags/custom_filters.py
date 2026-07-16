from django import template

register = template.Library()

@register.filter(name='getattr')
def getattr_filter(obj, attr):
    return getattr(obj, attr, 'none')


@register.filter(name='has_full_access')
def has_full_access(user, section):
    if not user or user.is_anonymous:
        return False

    if user.is_superuser:
        return True

    try:
        perms = user.custom_permissions
        return getattr(perms, section, 'none') == 'full'
    except Exception:
        return False


@register.filter(name='has_full_access')
def has_full_access(user, section):
    if not user or user.is_anonymous:
        return False

    if user.is_superuser:
        return True

    try:
        return getattr(user.custom_permissions, section) == 'full'
    except Exception:
        return False