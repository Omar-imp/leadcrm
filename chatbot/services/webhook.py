"""
Processes incoming WhatsApp messages.
Follows the Synergy Integrated Solutions bot script flow.
"""
import logging
from .whatsapp import send_text_message
from .ai import generate_response
from .crm import get_lead_context, create_demo_meeting_in_crm
from .utils import normalize_phone
from .prompts import HANDOFF_MESSAGE, DEMO_CONFIRMATION_TEMPLATE, NOT_INTERESTED_MESSAGE

logger = logging.getLogger(__name__)


def handle_incoming_message(phone_number: str, message_text: str) -> bool:
    """
    Main handler for incoming WhatsApp messages.
    Returns True if handled successfully.
    Never raises.
    """
    try:
        from chatbot.models import ChatSession, ChatMessage

        phone_number = normalize_phone(phone_number)

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
            logger.info('Session %s handed off — skipping auto-reply.', phone_number)
            return True

        # get CRM lead context
        lead_context = get_lead_context(phone_number)
        if lead_context.get('name') and not session.lead_name:
            session.lead_name = lead_context['name']
            session.save(update_fields=['lead_name'])

        # check for demo booking flow
        demo_reply = _check_demo_booking_flow(session, message_text)
        if demo_reply:
            reply_text = demo_reply
            should_handoff = False
        else:
            # generate AI response using Groq
            reply_text, should_handoff = generate_response(
                user_message=message_text,
                conversation_history=session.conversation_history or [],
                lead_context=lead_context,
            )

        if should_handoff:
            reply_text = HANDOFF_MESSAGE
            session.handed_off_to_human = True

        # update conversation history
        history = session.conversation_history or []
        history.append({'role': 'user', 'content': message_text})
        history.append({'role': 'assistant', 'content': reply_text})
        session.conversation_history = history[-30:]
        session.save()

        # send reply
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
        logger.exception('Failed to handle message from %s: %s', phone_number, exc)
        return False


def _check_demo_booking_flow(session, message_text: str):
    """
    Checks if we are in the middle of collecting demo booking details.
    Returns a reply string if we are, or None if normal AI flow should handle it.
    """
    try:
        from chatbot.models import DemoBooking
        from .prompts import DEMO_CONFIRMATION_TEMPLATE

        msg = message_text.strip().lower()

        # check for not interested
        if any(word in msg for word in ['not interested', 'no thanks', 'not right now', '3', 'no']):
            history = session.conversation_history or []
            if len(history) <= 4:
                return NOT_INTERESTED_MESSAGE

        # check if there's an incomplete demo booking for this session
        pending = DemoBooking.objects.filter(
            session=session,
            status='pending',
            client_name='',
        ).first()

        # check if we are actively collecting demo info
        booking_in_progress = DemoBooking.objects.filter(
            session=session,
            status='pending',
        ).exclude(client_name='').first()

        if not booking_in_progress:
            # check if message indicates demo interest
            demo_triggers = [
                'book', 'demo', 'schedule', 'consultation',
                'yes', 'book a demo', 'book my demo', '📅',
                'interested', 'proceed', 'let\'s go'
            ]
            if any(trigger in msg for trigger in demo_triggers):
                history = session.conversation_history or []
                if len(history) >= 2:
                    # start collecting demo info
                    DemoBooking.objects.create(
                        session=session,
                        client_name='__collecting__',
                        whatsapp_number=session.phone_number,
                        status='pending',
                    )
                    return (
                        "That's great! We would love to show you what we can do. 🎉\n\n"
                        "To get started, please tell me your *full name*:"
                    )
            return None

        # we are collecting — figure out what we have so far
        booking = booking_in_progress

        if booking.client_name == '__collecting__':
            booking.client_name = message_text.strip()
            booking.save()
            return "Thank you! 😊 What is your *company name*?"

        if not booking.company_name:
            booking.company_name = message_text.strip()
            booking.save()
            return (
                "Great! What *type of business* do you run?\n\n"
                "1️⃣ School/College\n"
                "2️⃣ Travel/Hajj/Umrah\n"
                "3️⃣ Retail/E-commerce\n"
                "4️⃣ Corporate/Office\n"
                "5️⃣ Real Estate\n"
                "6️⃣ Healthcare/Clinic\n"
                "7️⃣ Startup\n"
                "8️⃣ Service Business\n"
                "9️⃣ Not Sure"
            )

        if not booking.business_type:
            booking.business_type = message_text.strip()
            booking.save()
            return (
                "Perfect! Which *city/country* are you based in?"
            )

        if not booking.city:
            booking.city = message_text.strip()
            booking.save()
            return (
                "When would you prefer the demo?\n\n"
                "1️⃣ Today\n"
                "2️⃣ Tomorrow\n"
                "3️⃣ This Week\n"
                "4️⃣ Next Week"
            )

        if not booking.preferred_day:
            booking.preferred_day = message_text.strip()
            booking.save()
            return "What *time* works best for you? (e.g. 3:00 PM, 11:00 AM)"

        if not booking.preferred_time:
            booking.preferred_time = message_text.strip()
            booking.save()

            # all info collected — confirm booking
            booking.status = 'confirmed'
            booking.save()

            # create meeting in CRM
            meeting_id = create_demo_meeting_in_crm(booking)
            if meeting_id:
                booking.crm_meeting_id = meeting_id
                booking.save(update_fields=['crm_meeting_id'])

            return DEMO_CONFIRMATION_TEMPLATE.format(
                client_name=booking.client_name,
                company_name=booking.company_name or 'N/A',
                business_type=booking.business_type or 'N/A',
                preferred_time=f"{booking.preferred_day} at {booking.preferred_time}",
                whatsapp_number=booking.whatsapp_number,
            )

        return None

    except Exception as exc:
        logger.exception('Demo booking flow error: %s', exc)
        return None


def parse_meta_payload(data: dict) -> list:
    """Parses Meta WhatsApp Cloud API webhook payload."""
    results = []
    try:
        for entry in data.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})
                for msg in value.get('messages', []):
                    if msg.get('type') == 'text':
                        phone = msg.get('from', '')
                        text = msg.get('text', {}).get('body', '')
                        if phone and text:
                            results.append((phone, text))
    except Exception as exc:
        logger.error('Failed to parse Meta webhook payload: %s', exc)
    return results