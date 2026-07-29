from django import template

register = template.Library()


@register.filter(name='ecom_getattr')
def ecom_getattr_filter(obj, attr):
    return getattr(obj, attr, 'none')


@register.filter(name='ecom_has_full_access')
def ecom_has_full_access(user, section):
    if not user or user.is_anonymous:
        return False
    if user.is_superuser:
        return True
    try:
        perms = user.ecommerce_permissions
        return getattr(perms, section, 'none') == 'full'
    except Exception:
        return False


@register.filter(name='ecom_has_access')
def ecom_has_access(user, section):
    if not user or user.is_anonymous:
        return False
    if user.is_superuser:
        return True
    try:
        perms = user.ecommerce_permissions
        return getattr(perms, section, 'none') in ['full', 'view']
    except Exception:
        return False


@register.filter(name='ecom_is_view_only')
def ecom_is_view_only(user, section):
    if not user or user.is_anonymous:
        return False
    if user.is_superuser:
        return False
    try:
        perms = user.ecommerce_permissions
        return getattr(perms, section, 'none') == 'view'
    except Exception:
        return False
