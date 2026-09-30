"""
AI Lead Scoring using Groq.
Scores each lead 0-100 based on conversion probability.
"""
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


def score_lead(lead) -> tuple:
    """
    Scores a lead using Groq AI.
    Returns (score: int, reason: str)
    Score is 0-100 where 100 = highest conversion probability.
    Never raises.
    """
    try:
        from django.conf import settings
        from groq import Groq

        client = Groq(api_key=settings.GROQ_API_KEY)

        # build lead context for AI
        followup_count = lead.followups.count()
        done_followups = lead.followups.filter(status='done').count()
        comm_count = lead.communications.count()
        payment_count = lead.payments.count()

        prompt = f"""
You are a CRM sales analyst. Score this lead from 0 to 100 based on conversion probability.

LEAD DATA:
- Name: {lead.name}
- Source: {lead.get_lead_source_display()}
- Status: {lead.get_status_display()}
- Quotation Value: {lead.quotation}
- Total Followups: {followup_count}
- Completed Followups: {done_followups}
- Communications Logged: {comm_count}
- Payments Made: {payment_count}
- Days Since Created: {(timezone.now() - lead.created_at).days}
- Detail/Notes: {lead.detail or 'None'}

SCORING GUIDE:
- 80-100: Very likely to convert (positive status, high engagement, payments made)
- 60-79: Good chance (positive signals, active followups)
- 40-59: Moderate chance (some engagement, unclear intent)
- 20-39: Low chance (minimal engagement, no followups)
- 0-19: Very unlikely (lost status, no engagement, old lead)

Respond in this EXACT format, nothing else:
SCORE: [number between 0 and 100]
REASON: [one sentence explaining the score]
"""

        response = client.chat.completions.create(
            model='openai/gpt-oss-120b',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=100,
            temperature=0.3,
        )

        text = response.choices[0].message.content.strip()

        # parse score and reason
        score = 0
        reason = 'Unable to determine'

        for line in text.split('\n'):
            if line.startswith('SCORE:'):
                try:
                    score = int(line.replace('SCORE:', '').strip())
                    score = max(0, min(100, score))
                except ValueError:
                    pass
            elif line.startswith('REASON:'):
                reason = line.replace('REASON:', '').strip()

        return score, reason

    except Exception as exc:
        logger.error('Lead scoring failed for lead #%s: %s', lead.pk, exc)
        return 0, 'Scoring unavailable'


def update_lead_score(lead) -> bool:
    """
    Scores a lead and saves the result to the database.
    Returns True if successful.
    """
    try:
        score, reason = score_lead(lead)
        lead.ai_score = score
        lead.ai_score_reason = reason
        lead.ai_score_updated = timezone.now()
        lead.save(update_fields=['ai_score', 'ai_score_reason', 'ai_score_updated'])
        logger.info('Lead #%s scored: %s/100', lead.pk, score)
        return True
    except Exception as exc:
        logger.error('Failed to save score for lead #%s: %s', lead.pk, exc)
        return False


def get_score_color(score: int) -> str:
    """Returns a CSS color class based on score."""
    if score >= 80:
        return 'var(--green)'
    elif score >= 60:
        return '#2196f3'
    elif score >= 40:
        return 'var(--orange)'
    else:
        return 'var(--red)'