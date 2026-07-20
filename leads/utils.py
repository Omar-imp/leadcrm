import re


def normalize_phone_for_duplicate(phone: str) -> str:
    """Strips all non-digit characters for phone comparson."""
    if not phone:
        return ''
    return re.sub(r'\D', '', str(phone))
    
    
    
# leads/utils.py (ya jahan tumhara helper file hai)
from django.core.mail import send_mail

def send_lead_email(to_email, subject, message):
    send_mail(
        subject,
        message,
        None,  # DEFAULT_FROM_EMAIL use hoga
        [to_email],
        fail_silently=False,
    )