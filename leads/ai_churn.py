"""
AI Customer Churn Prediction using Groq.
Predicts which leads/customers are going cold or at risk of being lost.
"""
import logging
logger = logging.getLogger(__name__)


def predict_churn_risk(lead) -> tuple:
    """
    Predicts churn risk for a lead.
    Returns (risk_level: str, reason: str)
    risk_level: 'High', 'Medium', 'Low'
    """
    try:
        from django.conf import settings
        from django.utils import timezone
        from groq import Groq

        client = Groq(api_key=settings.GROQ_API_KEY)

        today = timezone.now()
        days_since_created = (today - lead.created_at).days

        last_comm = lead.communications.order_by('-created_at').first()
        days_since_comm = (
            (today - last_comm.created_at).days
            if last_comm else days_since_created
        )

        last_followup = lead.followups.order_by('-follow_up_date').first()
        days_since_followup = (
            (today - last_followup.created_at).days
            if last_followup else days_since_created
        )

        pending_followups = lead.followups.filter(status='pending').count()
        done_followups = lead.followups.filter(status='done').count()

        prompt = f"""
You are a CRM churn analyst. Predict the churn risk for this lead.

LEAD DATA:
- Name: {lead.name}
- Status: {lead.get_status_display()}
- Days Since Created: {days_since_created}
- Days Since Last Communication: {days_since_comm}
- Days Since Last Followup: {days_since_followup}
- Pending Followups: {pending_followups}
- Completed Followups: {done_followups}
- Quotation Value: {lead.quotation}
- Notes: {lead.detail or 'None'}

CHURN RISK GUIDE:
- High: No contact in 14+ days, lost status, no followups done
- Medium: No contact in 7-14 days, minimal engagement
- Low: Active engagement, recent communications, positive status

Respond in EXACT format:
RISK: [High/Medium/Low]
REASON: [one sentence]
ACTION: [one specific action to prevent churn]
"""

        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=150,
            temperature=0.2,
        )

        text = response.choices[0].message.content.strip()
        risk = 'Medium'
        reason = 'Unable to determine'
        action = 'Follow up immediately'

        for line in text.split('\n'):
            if line.startswith('RISK:'):
                risk = line.replace('RISK:', '').strip()
            elif line.startswith('REASON:'):
                reason = line.replace('REASON:', '').strip()
            elif line.startswith('ACTION:'):
                action = line.replace('ACTION:', '').strip()

        return risk, f"{reason} | Suggested: {action}"

    except Exception as exc:
        logger.error('Churn prediction failed for lead #%s: %s', lead.pk, exc)
        return 'Unknown', 'Prediction unavailable'


def update_churn_risk(lead) -> bool:
    """Updates and saves churn risk to database."""
    try:
        from django.utils import timezone
        risk, reason = predict_churn_risk(lead)
        lead.churn_risk = risk
        lead.churn_risk_reason = reason
        lead.churn_risk_updated = timezone.now()
        lead.save(update_fields=[
            'churn_risk', 'churn_risk_reason', 'churn_risk_updated'
        ])
        return True
    except Exception as exc:
        logger.error('Failed to save churn risk for lead #%s: %s', lead.pk, exc)
        return False


def get_high_churn_leads(limit=10):
    """Returns leads with high churn risk for dashboard display."""
    from .models import Lead
    return Lead.objects.filter(
        churn_risk='High'
    ).order_by('-churn_risk_updated')[:limit]