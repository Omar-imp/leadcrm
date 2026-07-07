"""
Meta WhatsApp Cloud API — ONLY provider used.
No Twilio, no third-party services.
"""
import logging
import requests
from django.conf import settings
from .utils import truncate_message
from .prompts import WELCOME_MESSAGE_TEMPLATE

logger = logging.getLogger(__name__)

META_API_VERSION = 'v18.0'
META_API_BASE_URL = 'https://graph.facebook.com'


def _get_headers():
    return {
        'Authorization': f'Bearer {settings.META_WHATSAPP_TOKEN}',
        'Content-Type': 'application/json',
    }


def _get_url():
    return (
        f'{META_API_BASE_URL}/{META_API_VERSION}'
        f'/{settings.META_PHONE_NUMBER_ID}/messages'
    )


def send_text_message(to: str, message: str) -> tuple:
    """
    Sends a plain text WhatsApp message via Meta Cloud API.

    Returns:
        (success: bool, message_id_or_error: str)
    Never raises.
    """
    token = getattr(settings, 'META_WHATSAPP_TOKEN', '')
    phone_number_id = getattr(settings, 'META_PHONE_NUMBER_ID', '')

    if not token or not phone_number_id:
        logger.warning(
            'Meta WhatsApp not configured. '
            'Set META_WHATSAPP_TOKEN and META_PHONE_NUMBER_ID in .env'
        )
        return False, 'Meta WhatsApp credentials not configured'

    message = truncate_message(message)

    payload = {
        'messaging_product': 'whatsapp',
        'recipient_type': 'individual',
        'to': to,
        'type': 'text',
        'text': {
            'preview_url': False,
            'body': message,
        },
    }

    try:
        response = requests.post(
            _get_url(),
            json=payload,
            headers=_get_headers(),
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            message_id = data.get('messages', [{}])[0].get('id', 'unknown')
            logger.info('WhatsApp message sent to %s — ID: %s', to, message_id)
            return True, message_id

        logger.error(
            'WhatsApp send failed to %s — %s: %s',
            to, response.status_code, response.text[:300]
        )
        return False, response.text[:300]

    except requests.exceptions.Timeout:
        logger.error('WhatsApp API timeout for %s', to)
        return False, 'Request timed out'

    except requests.exceptions.ConnectionError:
        logger.error('WhatsApp API connection error for %s', to)
        return False, 'Connection error'

    except Exception as exc:
        logger.exception('Unexpected WhatsApp error for %s: %s', to, exc)
        return False, str(exc)[:300]


def send_welcome_message(name: str, phone: str) -> tuple:
    """
    Sends a personalized welcome message to a new lead.
    Called automatically when a lead is created.
    """
    from .utils import normalize_phone, is_valid_phone

    normalized = normalize_phone(phone)

    if not is_valid_phone(normalized):
        logger.warning('Invalid phone number for welcome message: %s', phone)
        return False, f'Invalid phone number: {phone}'

    message = WELCOME_MESSAGE_TEMPLATE.format(name=name)
    return send_text_message(normalized, message)