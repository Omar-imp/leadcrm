"""
Processes incoming Meta WhatsApp Cloud API webhook events.
Parses the payload, generates AI response, sends reply.
"""
import logging
from .whatsapp import send_text_message
from .ai import generate_response
from .crm import get_lead_context
from .utils import normalize_phone
from .prompts import HANDOFF_MESSAGE

logger = logging.getLogger(__name__)


def handle_incoming_message(phone_number: str, message_text: str) -> bool:
    """
    Main handler for an incoming WhatsApp message.
    Called from views.py when Meta sends a webhook event.

    Returns True if handled successfully.
    Never raises.
    """
    try:
        from chatbot.models import ChatSession, ChatMessage

        phone_number = normalize_phone(phone_number)

        # get or create conversation session
        session, created = ChatSession.objects.get_or_create(
            phone_number=phone_number,
        )

        # log inbound message
        ChatMessage.objects.create(
            session=session,
            direction='inbound',
            message=message_text,
            delivered=True,
        )

        # if handed off to human — stop auto-replying
        if session.handed_off_to_human:
            logger.info(
                'Session %s is handed off — skipping auto-reply.', phone_number
            )
            return True

        # get CRM lead context for AI
        lead_context = get_lead_context(phone_number)
        if lead_context.get('name') and not session.lead_name:
            session.lead_name = lead_context['name']
            session.save(update_fields=['lead_name'])

        # generate AI response
        reply_text, should_handoff = generate_response(
            user_message=message_text,
            conversation_history=session.conversation_history or [],
            lead_context=lead_context,
        )

        if should_handoff:
            reply_text = HANDOFF_MESSAGE
            session.handed_off_to_human = True

        # update conversation history (keep last 20 messages)
        history = session.conversation_history or []
        history.append({'role': 'user', 'content': message_text})
        history.append({'role': 'assistant', 'content': reply_text})
        session.conversation_history = history[-20:]
        session.save()

        # send reply via Meta WhatsApp Cloud API
        success, result = send_text_message(phone_number, reply_text)

        # log outbound message
        ChatMessage.objects.create(
            session=session,
            direction='outbound',
            message=reply_text,
            whatsapp_message_id=result if success else None,
            delivered=success,
        )

        return success

    except Exception as exc:
        logger.exception(
            'Failed to handle message from %s: %s', phone_number, exc
        )
        return False


def parse_meta_payload(data: dict) -> list:
    """
    Parses a Meta WhatsApp Cloud API webhook POST payload.

    Returns a list of (phone_number, message_text) tuples
    for every text message found in the payload.
    """
    results = []
    try:
        for entry in data.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})
                for msg in value.get('messages', []):
                    if 'from' not in msg:
                        continue
                    if msg.get('from_me'):
                        continue
                    if msg.get('type') == 'text':
                        phone = msg.get('from', '')
                        text = msg.get('text', {}).get('body', '')
                        if phone and text:
                            results.append((phone, text))
    except Exception as exc:
        logger.error('Failed to parse Meta webhook payload: %s', exc)
    return results