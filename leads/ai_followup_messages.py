"""
AI Generated Follow-up Messages using Groq.
Writes personalized WhatsApp and email messages for each lead.
"""
import logging
logger = logging.getLogger(__name__)


def generate_followup_message(lead, channel='whatsapp') -> str:
    """
    Generates a personalized follow-up message for a lead.
    channel: 'whatsapp' or 'email'
    Returns message string.
    """
    try:
        from django.conf import settings
        from django.utils import timezone
        from groq import Groq

        client = Groq(api_key=settings.GROQ_API_KEY)

        days_old = (timezone.now() - lead.created_at).days
        last_comm = lead.communications.order_by('-created_at').first()
        last_comm_info = (
            f"{last_comm.get_comm_type_display()} on {last_comm.created_at:%d %b %Y}"
            if last_comm else "No previous contact"
        )

        if channel == 'whatsapp':
            format_instruction = (
                "Write a SHORT WhatsApp message (max 3 sentences). "
                "Use a friendly tone. Use 1-2 emojis naturally. "
                "No formal salutations. Sound human not robotic."
            )
        else:
            format_instruction = (
                "Write a professional email with Subject line and Body. "
                "Keep it under 100 words. Personalize it to this specific lead."
            )

        prompt = f"""
You are a sales assistant for Synergy Integrated Solutions, a software company.
Generate a follow-up message for this lead.

LEAD INFO:
- Name: {lead.name}
- Status: {lead.get_status_display()}
- Source: {lead.get_lead_source_display()}
- Quotation Value: {lead.quotation}
- Days Since First Contact: {days_old}
- Last Communication: {last_comm_info}
- Notes: {lead.detail or 'None'}

COMPANY: Synergy Integrated Solutions
SERVICES: ERP, CRM, Web/Mobile Apps, AI Automation, Digital Marketing

INSTRUCTIONS:
{format_instruction}

Generate ONLY the message, nothing else. No explanations.
"""

        response = client.chat.completions.create(
            model='openai/gpt-oss-120b',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=200,
            temperature=0.7,
        )

        return response.choices[0].message.content.strip()

    except Exception as exc:
        logger.error(
            'Follow-up message generation failed for lead #%s: %s',
            lead.pk, exc
        )
        return ''