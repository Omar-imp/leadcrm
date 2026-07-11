"""
AI Deal Closing Probability using Groq.
Different from lead scoring — focuses specifically on
how likely THIS deal is to close, not just lead quality.
"""
import logging
logger = logging.getLogger(__name__)


def predict_closing_probability(lead) -> tuple:
    """
    Predicts the probability of closing this deal.
    Returns (probability: int 0-100, reason: str)
    """
    try:
        from django.conf import settings
        from django.utils import timezone
        from groq import Groq

        client = Groq(api_key=settings.GROQ_API_KEY)

        followups = lead.followups.all()
        meetings = lead.meetings.count()
        quotations = lead.quotations.count()
        payments = lead.payments.count()
        days_old = (timezone.now() - lead.created_at).days
        comm_count = lead.communications.count()

        prompt = f"""
You are an expert sales analyst. Predict the probability of closing this deal.

DEAL DATA:
- Lead Name: {lead.name}
- Current Status: {lead.get_status_display()}
- Lead Source: {lead.get_lead_source_display()}
- Quotation Value: {lead.quotation}
- Days in Pipeline: {days_old}
- Followups Done: {followups.filter(status='done').count()}
- Pending Followups: {followups.filter(status='pending').count()}
- Meetings Held: {meetings}
- Quotations Sent: {quotations}
- Payments Made: {payments}
- Communications: {comm_count}
- Notes: {lead.detail or 'None'}

CLOSING PROBABILITY GUIDE:
- 90-100%: Deal is practically closed (payment made, contract signed)
- 70-89%: Very strong signals (multiple meetings, quotation accepted)
- 50-69%: Good progress (active engagement, quotation sent)
- 30-49%: Some interest but needs more work
- 10-29%: Early stage or losing momentum
- 0-9%: Very unlikely to close

Respond in EXACT format:
PROBABILITY: [0-100]
REASON: [one sentence]
RISK: [main risk factor in 5 words or less]
"""

        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=120,
            temperature=0.2,
        )

        text = response.choices[0].message.content.strip()
        probability = 0
        reason = 'Unable to determine'
        risk = 'Unknown'

        for line in text.split('\n'):
            if line.startswith('PROBABILITY:'):
                try:
                    probability = int(line.replace('PROBABILITY:', '').strip())
                    probability = max(0, min(100, probability))
                except ValueError:
                    pass
            elif line.startswith('REASON:'):
                reason = line.replace('REASON:', '').strip()
            elif line.startswith('RISK:'):
                risk = line.replace('RISK:', '').strip()

        return probability, reason, risk

    except Exception as exc:
        logger.error('Closing probability failed for lead #%s: %s', lead.pk, exc)
        return 0, 'Prediction unavailable', 'Unknown'


def update_closing_probability(lead) -> bool:
    """Updates and saves closing probability to database."""
    try:
        from django.utils import timezone
        probability, reason, risk = predict_closing_probability(lead)
        lead.closing_probability = probability
        lead.closing_probability_reason = f"{reason} | Risk: {risk}"
        lead.closing_probability_updated = timezone.now()
        lead.save(update_fields=[
            'closing_probability',
            'closing_probability_reason',
            'closing_probability_updated'
        ])
        return True
    except Exception as exc:
        logger.error('Failed to save closing probability for lead #%s: %s', lead.pk, exc)
        return False