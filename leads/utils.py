import re


def normalize_phone_for_duplicate(phone: str) -> str:
    """Strips all non-digit characters for phone comparson."""
    if not phone:
        return ''
    return re.sub(r'\D', '', str(phone))