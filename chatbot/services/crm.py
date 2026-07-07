"""
Read-only CRM helpers for the chatbot.
Looks up lead information by phone number.
NEVER modifies any existing CRM data.
"""
import logging

logger = logging.getLogger(__name__)


def get_lead_by_phone(phone_number: str):
    """
    Finds a Lead in the CRM by phone number.
    Tries multiple formats to maximize match rate.
    Returns Lead object or None.
    """
    try:
        from leads.models import Lead
        from .utils import normalize_phone

        normalized = normalize_phone(phone_number)

        # try exact match
        lead = Lead.objects.filter(contact_number=phone_number).first()
        if lead:
            return lead

        # try normalized E.164 format
        lead = Lead.objects.filter(contact_number=normalized).first()
        if lead:
            return lead

        # try Pakistani local format (0300...)
        if normalized.startswith('+92'):
            local_format = '0' + normalized[3:]
            lead = Lead.objects.filter(contact_number=local_format).first()
            if lead:
                return lead

        return None

    except Exception as exc:
        logger.error('CRM lead lookup failed for %s: %s', phone_number, exc)
        return None


def get_lead_context(phone_number: str) -> dict:
    """
    Returns a dictionary of lead info to give the AI context
    about who it is talking to.
    Returns empty dict if lead not found.
    """
    lead = get_lead_by_phone(phone_number)
    if not lead:
        return {}

    return {
    "name": lead.name,
    "email": lead.email or "",
    "phone": lead.contact_number,
    "lead_source": lead.get_lead_source_display(),
    "status": lead.get_status_display(),
    "quotation": str(lead.quotation or ""),
    "created_at": lead.created_at.strftime("%d %B %Y") if hasattr(lead, "created_at") and lead.created_at else "",
    "notes": getattr(lead, "notes", ""),
    "assigned_to": str(getattr(lead, "assigned_to", "")),
}