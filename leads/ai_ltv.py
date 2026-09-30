"""
AI Customer Lifetime Value estimation using Groq.
Estimates total revenue a customer will generate over their lifetime.
"""
import logging
logger = logging.getLogger(__name__)


def estimate_lifetime_value(lead) -> tuple:
    """
    Estimates customer lifetime value.
    Returns (ltv: float, reason: str)
    """
    try:
        from django.conf import settings
        from django.utils import timezone
        from groq import Groq

        client = Groq(api_key=settings.GROQ_API_KEY)

        payments = lead.payments.all()
        total_paid = float(sum(p.amount for p in payments))
        payment_count = payments.count()
        days_old = (timezone.now() - lead.created_at).days
        monthly_value = (total_paid / max(days_old, 1)) * 30

        prompt = f"""
You are a customer value analyst for a software company.
Estimate the total lifetime value of this customer.

CUSTOMER DATA:
- Name: {lead.name}
- Status: {lead.get_status_display()}
- Source: {lead.get_lead_source_display()}
- Original Quotation: {lead.quotation}
- Total Paid So Far: {total_paid}
- Number of Payments: {payment_count}
- Days as Customer: {days_old}
- Estimated Monthly Value: {monthly_value:.0f}
- Notes: {lead.detail or 'None'}

Consider:
- Renewal probability
- Upsell potential
- Referral value
- Average software company customer lifetime (2-5 years)
- Monthly recurring potential

Respond in EXACT format:
LTV: [estimated lifetime value as a number only]
TIMEFRAME: [expected customer lifetime e.g. 2 years]
REASON: [one sentence explaining the estimate]
GROWTH_POTENTIAL: [High/Medium/Low]
"""

        response = client.chat.completions.create(
            model='openai/gpt-oss-120b',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=150,
            temperature=0.3,
        )

        text = response.choices[0].message.content.strip()
        ltv = 0.0
        reason = 'Unable to estimate'
        timeframe = 'Unknown'
        growth = 'Medium'

        for line in text.split('\n'):
            if line.startswith('LTV:'):
                try:
                    ltv = float(
                        line.replace('LTV:', '').strip().replace(',', '')
                    )
                except ValueError:
                    pass
            elif line.startswith('REASON:'):
                reason = line.replace('REASON:', '').strip()
            elif line.startswith('TIMEFRAME:'):
                timeframe = line.replace('TIMEFRAME:', '').strip()
            elif line.startswith('GROWTH_POTENTIAL:'):
                growth = line.replace('GROWTH_POTENTIAL:', '').strip()

        full_reason = f"{reason} | Timeframe: {timeframe} | Growth: {growth}"
        return ltv, full_reason

    except Exception as exc:
        logger.error('LTV estimation failed for lead #%s: %s', lead.pk, exc)
        return 0.0, 'Estimation unavailable'


def update_lifetime_value(lead) -> bool:
    """Updates and saves LTV to database."""
    try:
        from django.utils import timezone
        ltv, reason = estimate_lifetime_value(lead)
        lead.lifetime_value = ltv
        lead.lifetime_value_reason = reason
        lead.lifetime_value_updated = timezone.now()
        lead.save(update_fields=[
            'lifetime_value', 'lifetime_value_reason', 'lifetime_value_updated'
        ])
        return True
    except Exception as exc:
        logger.error('Failed to save LTV for lead #%s: %s', lead.pk, exc)
        return False