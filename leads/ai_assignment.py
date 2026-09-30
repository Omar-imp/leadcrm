"""
AI Smart Lead Assignment using Groq.
Analyzes salesperson workload and performance to assign the best SPO to a lead.
"""
import logging
logger = logging.getLogger(__name__)


def get_spo_stats() -> list:
    """Builds a stats summary for each salesperson."""
    try:
        from .models import SalesPerson, Lead

        stats = []
        for spo in SalesPerson.objects.select_related('user').all():
            spo_leads = Lead.objects.filter(spo=spo)
            total = spo_leads.count()
            converted = spo_leads.filter(status='converted').count()
            active = spo_leads.filter(
                status__in=['new', 'positive', 'quotation']
            ).count()
            conversion_rate = round(
                (converted / total * 100) if total > 0 else 0, 1
            )
            stats.append({
                'id': spo.pk,
                'name': spo.name,
                'total_leads': total,
                'active_leads': active,
                'converted': converted,
                'conversion_rate': conversion_rate,
            })
        return stats

    except Exception as exc:
        logger.error('Failed to get SPO stats: %s', exc)
        return []


def assign_lead_with_ai(lead) -> bool:
    """
    Uses Groq to pick the best salesperson for a lead.
    Returns True if assignment was made.
    """
    try:
        from django.conf import settings
        from groq import Groq
        from .models import SalesPerson

        spo_stats = get_spo_stats()
        if not spo_stats:
            logger.warning('No salespersons found for assignment.')
            return False

        client = Groq(api_key=settings.GROQ_API_KEY)

        spo_summary = '\n'.join([
            f"- {s['name']} (ID:{s['id']}): "
            f"{s['active_leads']} active leads, "
            f"{s['conversion_rate']}% conversion rate, "
            f"{s['total_leads']} total leads"
            for s in spo_stats
        ])

        prompt = f"""
You are a CRM sales manager. Assign the best salesperson to this new lead.

NEW LEAD:
- Name: {lead.name}
- Source: {lead.get_lead_source_display()}
- Quotation: {lead.quotation}
- Detail: {lead.detail or 'None'}

AVAILABLE SALESPERSONS:
{spo_summary}

RULES:
- Prefer salesperson with lower active leads (balanced workload)
- Prefer higher conversion rate if workload is similar
- Consider lead value — high quotation leads go to top performer

Respond in this EXACT format, nothing else:
ASSIGN_TO_ID: [salesperson ID number]
REASON: [one sentence explaining why]
"""

        response = client.chat.completions.create(
            model='openai/gpt-oss-120b',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=100,
            temperature=0.2,
        )

        text = response.choices[0].message.content.strip()

        spo_id = None
        reason = ''
        for line in text.split('\n'):
            if line.startswith('ASSIGN_TO_ID:'):
                try:
                    spo_id = int(line.replace('ASSIGN_TO_ID:', '').strip())
                except ValueError:
                    pass
            elif line.startswith('REASON:'):
                reason = line.replace('REASON:', '').strip()

        if spo_id:
            spo = SalesPerson.objects.filter(pk=spo_id).first()
            if spo:
                lead.spo = spo
                lead.save(update_fields=['spo'])
                logger.info(
                    'Lead #%s assigned to %s — %s',
                    lead.pk, spo.name, reason
                )
                return True

        return False

    except Exception as exc:
        logger.error('Smart assignment failed for lead #%s: %s', lead.pk, exc)
        return False