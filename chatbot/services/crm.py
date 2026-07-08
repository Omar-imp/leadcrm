"""
Read-only CRM helpers for the chatbot.
Also handles creating meetings in CRM when demos are booked.
NEVER modifies existing CRM leads or contacts directly.
"""
import logging

logger = logging.getLogger(__name__)


def get_lead_by_phone(phone_number: str):
    try:
        from leads.models import Lead
        from .utils import normalize_phone

        normalized = normalize_phone(phone_number)

        lead = Lead.objects.filter(contact_number=phone_number).first()
        if lead:
            return lead

        lead = Lead.objects.filter(contact_number=normalized).first()
        if lead:
            return lead

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
    lead = get_lead_by_phone(phone_number)
    if not lead:
        return {}
    return {
        'name': lead.name,
        'email': lead.email or '',
        'lead_source': lead.get_lead_source_display(),
        'quotation': str(lead.quotation),
        'status': lead.get_status_display(),
    }


def create_demo_meeting_in_crm(booking) -> int | None:
    """
    Creates a Meeting record in the CRM when a demo is booked via WhatsApp.
    Returns the meeting ID or None if it fails.
    """
    try:
        from leads.models import Meeting
        from django.utils import timezone
        import datetime

        # find the lead in CRM by phone
        lead = get_lead_by_phone(booking.whatsapp_number)

        # build a scheduled datetime — default to tomorrow noon if not specific
        try:
            scheduled_at = timezone.now() + datetime.timedelta(days=1)
            scheduled_at = scheduled_at.replace(hour=12, minute=0, second=0)
        except Exception:
            scheduled_at = timezone.now() + datetime.timedelta(days=1)

        title = f"Demo — {booking.client_name} ({booking.company_name or 'Unknown Company'})"

        meeting = Meeting.objects.create(
            title=title,
            meeting_type='demo',
            status='scheduled',
            scheduled_at=scheduled_at,
            duration_minutes=60,
            location='Online / WhatsApp',
            agenda=(
                f"Business Type: {booking.business_type or 'Not specified'}\n"
                f"Preferred Time: {booking.preferred_day} — {booking.preferred_time}\n"
                f"WhatsApp: {booking.whatsapp_number}\n"
                f"City: {booking.city or 'Not specified'}"
            ),
            notes=f"Demo booked via WhatsApp chatbot for {booking.company_name or 'unknown company'}.",
            lead=lead,
        )

        logger.info(
            'Created CRM meeting #%s for demo booking: %s',
            meeting.pk, booking.client_name
        )
        return meeting.pk

    except Exception as exc:
        logger.error('Failed to create CRM meeting for demo booking: %s', exc)
        return None