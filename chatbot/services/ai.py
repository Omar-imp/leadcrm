"""
AI response generation using Groq API.
Groq is faster and cheaper than OpenAI for this use case.
Falls back to rule-based responses if GROQ_API_KEY is not set.
"""
import logging
from .prompts import SYSTEM_PROMPT, HANDOFF_MESSAGE, ERROR_MESSAGE

logger = logging.getLogger(__name__)

HANDOFF_TRIGGER_PHRASES = [
    'connect you with',
    'human representative',
    'specialist',
    'team member will contact',
    'someone will reach out',
]


def generate_response(
    user_message: str,
    conversation_history: list,
    lead_context: dict = None,
) -> tuple:
    """
    Generates an AI response using Groq.

    Returns:
        (response_text: str, should_handoff: bool)
    """
    try:
        from django.conf import settings
        groq_key = getattr(settings, 'GROQ_API_KEY', '')

        if groq_key:
            return _call_groq(
                user_message,
                conversation_history,
                lead_context or {}
            )

        logger.warning('GROQ_API_KEY not set — using placeholder responses.')
        return _placeholder_response(user_message), False

    except Exception as exc:
        logger.exception('AI generation error: %s', exc)
        return ERROR_MESSAGE, False


def _build_context_string(lead_context: dict) -> str:
    if not lead_context:
        return ''
    name = lead_context.get('name', 'the customer')
    source = lead_context.get('lead_source', 'unknown')
    return (
        f"You are speaking with {name}, "
        f"who contacted us via {source}. "
        f"Tailor your responses to their needs."
    )


def _call_groq(
    user_message: str,
    conversation_history: list,
    lead_context: dict,
) -> tuple:
    """Calls Groq API to generate a response."""
    try:
        from groq import Groq
        from django.conf import settings

        client = Groq(api_key=settings.GROQ_API_KEY)

        system_content = SYSTEM_PROMPT
        context_str = _build_context_string(lead_context)
        if context_str:
            system_content += '\n\n' + context_str

        messages = [{'role': 'system', 'content': system_content}]

        for entry in conversation_history[-10:]:
            messages.append({
                'role': entry.get('role', 'user'),
                'content': entry.get('content', ''),
            })

        messages.append({'role': 'user', 'content': user_message})

        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=messages,
            max_tokens=300,
            temperature=0.7,
        )

        reply = response.choices[0].message.content.strip()
        should_handoff = any(
            p in reply.lower() for p in HANDOFF_TRIGGER_PHRASES
        )

        return reply, should_handoff

    except Exception as exc:
        logger.exception('Groq API call failed: %s', exc)
        return ERROR_MESSAGE, False


def _placeholder_response(message: str) -> str:
    m = message.lower()

    if any(w in m for w in ['hi', 'hello', 'hey', 'salam']):
        return "Hello! Thanks for reaching out. How can I help you today?"

    if any(w in m for w in ['price', 'cost', 'quote', 'budget']):
        return (
            "Our pricing is customized based on your requirements. "
            "Could you tell me more about your project?"
        )

    if any(w in m for w in ['service', 'offer', 'build', 'develop']):
        return (
            "We build custom web apps, mobile apps, AI solutions and CRM systems. "
            "What kind of project do you have in mind?"
        )

    return (
        "Thanks for your message! "
        "Our team will get back to you shortly."
    )