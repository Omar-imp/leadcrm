from django.utils import timezone
from .models import (Lead, FollowUp, Payment, ScheduledPayment,
                     Company, Contact, Opportunity, Quotation,
                     Project, Meeting, GeneralTask)


def sidebar_counts(request):
    if not request.user.is_authenticated:
        return {}
    today = timezone.localdate()
    leads = Lead.objects.all()
    followups = FollowUp.objects.all()
    return {
        'sidebar_counts': {
            'total': leads.count(),
            'new': leads.filter(status='new').count(),
            'positive': leads.filter(status='positive').count(),
            'lost': leads.filter(status='lost').count(),
            'quotation': leads.filter(status='quotation').count(),
            'convert': leads.filter(status='converted').count(),
            'payment_advance': Payment.objects.filter(payment_type='advance').count(),
            'payment_full': Payment.objects.filter(payment_type='full').count(),
            'payment_scheduled': ScheduledPayment.objects.count(),
            'followup_pending': followups.filter(status='pending').count(),
            'followup_today': followups.filter(status='pending', follow_up_date__date=today).count(),
            'followup_next': followups.filter(status='pending', follow_up_date__date__gt=today).count(),
            'followup_done': followups.filter(status='done').count(),
            'companies': Company.objects.count(),
            'contacts': Contact.objects.count(),
            'opportunities': Opportunity.objects.exclude(stage__in=['won', 'lost']).count(),
            'won': Opportunity.objects.filter(stage='won').count(),
            'quotations': Quotation.objects.filter(status__in=['draft', 'sent']).count(),
            'projects': Project.objects.filter(status__in=['planning', 'active']).count(),
            'meetings_today': Meeting.objects.filter(scheduled_at__date=today, status='scheduled').count(),
            'meetings_upcoming': Meeting.objects.filter(scheduled_at__date__gte=today, status='scheduled').count(),
            'tasks_pending': GeneralTask.objects.filter(status__in=['todo', 'in_progress']).count(),
            'tasks_overdue': GeneralTask.objects.filter(due_date__lt=today, status__in=['todo', 'in_progress']).count(),
        }
    }