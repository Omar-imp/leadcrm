"""
Duplicate lead detection.
Checks phone number and email against existing leads.
"""
import logging

logger = logging.getLogger(__name__)


def find_duplicate(lead) -> object | None:
    """
    Checks if a lead with the same phone or email already exists.
    Returns the existing lead if found, None otherwise.
    Excludes the lead itself from the check.
    """
    from .models import Lead
    from .utils import normalize_phone_for_duplicate

    # normalize phone for comparison
    phone = normalize_phone_for_duplicate(lead.contact_number)

    # check phone number match
    if phone:
        existing = Lead.objects.filter(
            contact_number__icontains=phone[-9:]  # last 9 digits
        ).exclude(pk=lead.pk).first()
        if existing:
            return existing

    # check email match
    if lead.email:
        existing = Lead.objects.filter(
            email__iexact=lead.email
        ).exclude(pk=lead.pk).first()
        if existing:
            return existing

    return None


def check_and_mark_duplicate(lead) -> bool:
    """
    Checks if lead is a duplicate and marks it.
    Returns True if duplicate found.
    """
    try:
        duplicate_of = find_duplicate(lead)
        if duplicate_of:
            lead.is_duplicate = True
            lead.duplicate_of = duplicate_of
            lead.save(update_fields=['is_duplicate', 'duplicate_of'])
            logger.info(
                'Lead #%s marked as duplicate of Lead #%s',
                lead.pk, duplicate_of.pk
            )
            return True
        return False
    except Exception as exc:
        logger.error('Duplicate check failed for lead #%s: %s', lead.pk, exc)
        return False