"""
AI Sales Forecasting using Groq.
Predicts next month revenue and pipeline health.
"""
import logging
logger = logging.getLogger(__name__)


def generate_sales_forecast() -> dict:
    """
    Analyzes current pipeline and predicts next month revenue.
    Returns dict with forecast data.
    """
    try:
        from django.conf import settings
        from django.utils import timezone
        from django.db.models import Sum
        from groq import Groq
        from .models import Lead, Payment, Opportunity

        client = Groq(api_key=settings.GROQ_API_KEY)

        today = timezone.localdate()
        this_month_start = today.replace(day=1)

        # current pipeline data
        total_leads = Lead.objects.count()
        new_leads = Lead.objects.filter(status='new').count()
        positive_leads = Lead.objects.filter(status='positive').count()
        quotation_leads = Lead.objects.filter(status='quotation').count()
        converted_leads = Lead.objects.filter(status='converted').count()
        lost_leads = Lead.objects.filter(status='lost').count()

        # revenue data
        total_revenue = Payment.objects.aggregate(
            total=Sum('amount')
        )['total'] or 0
        this_month_revenue = Payment.objects.filter(
            date__date__gte=this_month_start
        ).aggregate(total=Sum('amount'))['total'] or 0

        # pipeline value
        pipeline_value = Lead.objects.filter(
            status__in=['positive', 'quotation']
        ).aggregate(total=Sum('quotation'))['total'] or 0

        # avg scores
        avg_score = Lead.objects.filter(
            ai_score__gt=0
        ).aggregate(
            avg=Sum('ai_score')
        )['avg'] or 0

        scored_count = Lead.objects.filter(ai_score__gt=0).count()
        avg_score = round(avg_score / scored_count, 1) if scored_count > 0 else 0

        prompt = f"""
You are a sales forecasting expert. Analyze this CRM data and forecast next month's revenue.

CURRENT PIPELINE STATUS:
- Total Leads: {total_leads}
- New Leads: {new_leads}
- Positive Leads: {positive_leads}
- Quotation Stage: {quotation_leads}
- Converted This Month: {converted_leads}
- Lost Leads: {lost_leads}
- Pipeline Value (positive+quotation): {pipeline_value}
- This Month Revenue So Far: {this_month_revenue}
- Total Revenue All Time: {total_revenue}
- Average Lead Score: {avg_score}/100

FORECAST INSTRUCTIONS:
Based on the conversion rates and pipeline value, predict:
1. Estimated next month revenue range
2. Expected number of conversions
3. Pipeline health (Excellent/Good/Fair/Poor)
4. Top 3 recommendations to improve sales

Respond in EXACT format:
REVENUE_MIN: [number]
REVENUE_MAX: [number]
EXPECTED_CONVERSIONS: [number]
PIPELINE_HEALTH: [Excellent/Good/Fair/Poor]
RECOMMENDATION_1: [action]
RECOMMENDATION_2: [action]
RECOMMENDATION_3: [action]
SUMMARY: [2 sentence overall forecast summary]
"""

        response = client.chat.completions.create(
            model='openai/gpt-oss-120b',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=300,
            temperature=0.3,
        )

        text = response.choices[0].message.content.strip()

        result = {
            'revenue_min': 0,
            'revenue_max': 0,
            'expected_conversions': 0,
            'pipeline_health': 'Unknown',
            'recommendations': [],
            'summary': '',
            'this_month_revenue': this_month_revenue,
            'pipeline_value': pipeline_value,
            'total_leads': total_leads,
            'converted_leads': converted_leads,
        }

        for line in text.split('\n'):
            if line.startswith('REVENUE_MIN:'):
                try:
                    result['revenue_min'] = int(
                        line.replace('REVENUE_MIN:', '').strip()
                    )
                except ValueError:
                    pass
            elif line.startswith('REVENUE_MAX:'):
                try:
                    result['revenue_max'] = int(
                        line.replace('REVENUE_MAX:', '').strip()
                    )
                except ValueError:
                    pass
            elif line.startswith('EXPECTED_CONVERSIONS:'):
                try:
                    result['expected_conversions'] = int(
                        line.replace('EXPECTED_CONVERSIONS:', '').strip()
                    )
                except ValueError:
                    pass
            elif line.startswith('PIPELINE_HEALTH:'):
                result['pipeline_health'] = line.replace(
                    'PIPELINE_HEALTH:', ''
                ).strip()
            elif line.startswith('RECOMMENDATION_'):
                rec = ':'.join(line.split(':')[1:]).strip()
                if rec:
                    result['recommendations'].append(rec)
            elif line.startswith('SUMMARY:'):
                result['summary'] = line.replace('SUMMARY:', '').strip()

        return result

    except Exception as exc:
        logger.error('Sales forecasting failed: %s', exc)
        return {
            'error': 'Forecasting unavailable',
            'revenue_min': 0,
            'revenue_max': 0,
        }