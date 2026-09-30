"""
AI Meeting Summary generator using Groq.
Takes raw meeting notes and produces structured summaries with action items.
"""
import logging
logger = logging.getLogger(__name__)


def generate_meeting_summary(meeting) -> str:
    """
    Generates a structured AI summary of a meeting.
    Returns summary string.
    """
    try:
        from django.conf import settings
        from groq import Groq

        if not meeting.notes and not meeting.agenda and not meeting.action_items:
            return 'No meeting notes available to summarize.'

        client = Groq(api_key=settings.GROQ_API_KEY)

        prompt = f"""
You are an expert meeting summarizer for a CRM system.
Summarize this meeting in a clear, structured format.

MEETING DETAILS:
- Title: {meeting.title}
- Type: {meeting.get_meeting_type_display()}
- Date: {meeting.scheduled_at:%d %b %Y at %H:%M}
- Duration: {meeting.duration_minutes} minutes
- Attendees: {', '.join([u.username for u in meeting.attendees.all()]) or 'Not recorded'}

AGENDA:
{meeting.agenda or 'Not provided'}

NOTES / MINUTES:
{meeting.notes or 'Not provided'}

EXISTING ACTION ITEMS:
{meeting.action_items or 'None recorded'}

Generate a summary in this EXACT format:

SUMMARY:
[2-3 sentences covering what was discussed and decided]

KEY DECISIONS:
- [decision 1]
- [decision 2]

ACTION ITEMS:
- [action item with owner if mentioned]
- [action item with deadline if mentioned]

NEXT STEPS:
[what happens next, 1-2 sentences]
"""

        response = client.chat.completions.create(
            model='openai/gpt-oss-120b',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=400,
            temperature=0.3,
        )

        return response.choices[0].message.content.strip()

    except Exception as exc:
        logger.error(
            'Meeting summary failed for meeting #%s: %s',
            meeting.pk, exc
        )
        return 'Summary generation failed.'


def save_meeting_summary(meeting) -> bool:
    """Generates and saves AI summary to the meeting record."""
    try:
        from django.utils import timezone
        summary = generate_meeting_summary(meeting)
        meeting.ai_summary = summary
        meeting.ai_summary_updated = timezone.now()
        meeting.save(update_fields=['ai_summary', 'ai_summary_updated'])
        return True
    except Exception as exc:
        logger.error('Failed to save summary for meeting #%s: %s', meeting.pk, exc)
        return False