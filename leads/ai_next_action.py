"""
AI Next Best Action recommendations using Groq.
Tells the salesperson exactly what to do next with each lead.
"""
import logging
logger = logging.getLogger(__name__)


def get_next_action(lead) -> dict:
    """
    Analyzes lead history and recommends the next best action.
    Returns dict with action, priority, reason and deadline.
    Never raises.
    """
    try:
        from django.conf import settings
        from django.utils import timezone
        from groq import Groq

        client = Groq(api_key=settings.GROQ_API_KEY)

        # gather lead context
        followups = lead.followups.all()
        pending_followups = followups.filter(status='pending').count()
        done_followups = followups.filter(status='done').count()
        last_followup = followups.order_by('-created_at').first()
        comm_count = lead.communications.count()
        last_comm = lead.communications.order_by('-created_at').first()
        days_old = (timezone.now() - lead.created_at).days
        meetings = lead.meetings.count()

        last_followup_date = (
            last_followup.follow_up_date.strftime('%d %b %Y')
            if last_followup else 'Never'
        )
        last_comm_type = (
            last_comm.get_comm_type_display()
            if last_comm else 'None'
        )

        prompt = f"""
You are an expert CRM sales coach. Recommend the single most important next action for this lead.

LEAD SUMMARY:
- Name: {lead.name}
- Status: {lead.get_status_display()}
- Source: {lead.get_lead_source_display()}
- Quotation: {lead.quotation}
- Days Since Created: {days_old}
- Pending Followups: {pending_followups}
- Completed Followups: {done_followups}
- Last Followup Date: {last_followup_date}
- Communications Logged: {comm_count}
- Last Communication Type: {last_comm_type}
- Meetings Scheduled: {meetings}
- Notes: {lead.detail or 'None'}

POSSIBLE ACTIONS:
- Send WhatsApp message
- Make a phone call
- Schedule a demo
- Send a proposal/quotation
- Follow up on sent quotation
- Negotiate and close deal
- Re-engage cold lead
- Mark as lost and move on

Respond in this EXACT format:
ACTION: [the single best next action]
PRIORITY: [High / Medium / Low]
DEADLINE: [Today / Within 24 hours / Within 3 days / This week]
REASON: [one sentence explaining why this action now]
"""

        response = client.chat.completions.create(
            model='openai/gpt-oss-120b',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=150,
            temperature=0.3,
        )

        text = response.choices[0].message.content.strip()

        result = {
            'action': 'Follow up with lead',
            'priority': 'Medium',
            'deadline': 'This week',
            'reason': 'No specific recommendation available',
        }

        for line in text.split('\n'):
            if line.startswith('ACTION:'):
                result['action'] = line.replace('ACTION:', '').strip()
            elif line.startswith('PRIORITY:'):
                result['priority'] = line.replace('PRIORITY:', '').strip()
            elif line.startswith('DEADLINE:'):
                result['deadline'] = line.replace('DEADLINE:', '').strip()
            elif line.startswith('REASON:'):
                result['reason'] = line.replace('REASON:', '').strip()

        return result

    except Exception as exc:
        logger.error('Next action failed for lead #%s: %s', lead.pk, exc)
        return {
            'action': 'Review lead manually',
            'priority': 'Medium',
            'deadline': 'This week',
            'reason': 'AI recommendation unavailable',
        }