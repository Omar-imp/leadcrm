from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


ECOM_URL_SECTION_MAP = {
    'products': ['/ecommerce/products/'],
    'categories': ['/ecommerce/categories/'],
    'customers': ['/ecommerce/customers/'],
    'orders': ['/ecommerce/orders/'],
    'inventory': ['/ecommerce/inventory/'],
    'payments': ['/ecommerce/payments/'],
    'shipping': ['/ecommerce/shipments/'],
    'returns': ['/ecommerce/returns/'],
    'reports': ['/ecommerce/reports/'],
}


def get_ecom_section_for_path(path):
    for section, prefixes in ECOM_URL_SECTION_MAP.items():
        for prefix in prefixes:
            if path.startswith(prefix):
                return section
    return None


def block_ecommerce_view_only(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if (
            request.method == "POST"
            and request.user.is_authenticated
            and not request.user.is_superuser
        ):
            try:
                perms = request.user.ecommerce_permissions
                path = request.path
                section = get_ecom_section_for_path(path)

                if section and getattr(perms, section, 'none') == 'view':
                    messages.error(request, f'You only have view access to {section}.')
                    return redirect('ecommerce_dashboard')
            except Exception as e:
                print("ECOM BLOCK ERROR:", e)
        return view_func(request, *args, **kwargs)
    return wrapper
