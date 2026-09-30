"""
AI Upsell and Cross-sell Recommendations using Groq.
Suggests additional services to offer existing customers.
"""
import logging
logger = logging.getLogger(__name__)


def get_upsell_recommendations(lead) -> dict:
    """
    Analyzes a converted lead and recommends upsell/cross-sell opportunities.
    Returns dict with recommendations.
    """
    try:
        from django.conf import settings
        from groq import Groq

        client = Groq(api_key=settings.GROQ_API_KEY)

        payments = lead.payments.all()
        total_paid = sum(p.amount for p in payments)
        comm_count = lead.communications.count()
        projects = lead.opportunities.count() if hasattr(lead, 'opportunities') else 0

        prompt = f"""
You are a sales strategist for Synergy Integrated Solutions, a software company.
Recommend upsell and cross-sell opportunities for this existing customer.

CUSTOMER DATA:
- Name: {lead.name}
- Current Status: {lead.get_status_display()}
- Lead Source: {lead.get_lead_source_display()}
- Original Quotation: {lead.quotation}
- Total Paid: {total_paid}
- Communications: {comm_count}
- Notes: {lead.detail or 'None'}

OUR SERVICES:
1. ERP & CRM Systems
2. Website & Mobile App Development
3. AI Automation & WhatsApp Chatbot
4. Digital Marketing & Lead Generation
5. Custom Software Development
6. Annual Maintenance Contract (AMC)
7. Staff Training & Onboarding
8. Cloud Hosting & DevOps
9. SEO & Content Marketing
10. Business Intelligence Dashboard

Based on what this customer likely already has and their business type,
recommend the 3 best upsell/cross-sell opportunities.

Respond in EXACT format:
UPSELL_1: [service name] | [one sentence why this customer needs it]
UPSELL_2: [service name] | [one sentence why this customer needs it]
UPSELL_3: [service name] | [one sentence why this customer needs it]
TIMING: [best time to approach — e.g. immediately, after 3 months, at renewal]
APPROACH: [one sentence on how to pitch these]
"""

        response = client.chat.completions.create(
            model='openai/gpt-oss-120b',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=300,
            temperature=0.5,
        )

        text = response.choices[0].message.content.strip()

        result = {
            'upsells': [],
            'timing': '',
            'approach': '',
        }

        for line in text.split('\n'):
            if line.startswith('UPSELL_'):
                parts = line.split(':', 1)
                if len(parts) > 1:
                    upsell_content = parts[1].strip()
                    if '|' in upsell_content:
                        service, reason = upsell_content.split('|', 1)
                        result['upsells'].append({
                            'service': service.strip(),
                            'reason': reason.strip(),
                        })
            elif line.startswith('TIMING:'):
                result['timing'] = line.replace('TIMING:', '').strip()
            elif line.startswith('APPROACH:'):
                result['approach'] = line.replace('APPROACH:', '').strip()

        return result

    except Exception as exc:
        logger.error('Upsell recommendations failed for lead #%s: %s', lead.pk, exc)
        return {'upsells': [], 'timing': '', 'approach': ''}