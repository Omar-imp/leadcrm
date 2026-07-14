from django.utils import timezone
from .permissions import get_allowed_sections
from .models import (Lead, FollowUp, Payment, ScheduledPayment,
                     Company, Contact, Opportunity, Quotation,
                     Project, Meeting, GeneralTask,
                     CommunicationLog, Ticket, ActivityLog,
                     Document, Contract, Notification)


def sidebar_counts(request):
    if not request.user.is_authenticated:
        return {}

    today = timezone.localdate()
    leads = Lead.objects.all()
    followups = FollowUp.objects.all()

    # get allowed sections and view-only sections
    if request.user.is_superuser:
        allowed_sections = ['*']
        view_only_sections = []
    else:
        try:
            perms = request.user.custom_permissions
            allowed_sections = [
                s for s in perms.ALL_SECTIONS
                if perms.has_access(s)
            ]
            view_only_sections = [
                s for s in perms.ALL_SECTIONS
                if perms.is_view_only(s)
            ]
        except Exception:
            from .permissions import get_allowed_sections
            role = getattr(
                getattr(request.user, 'profile', None), 'role', None
            )
            allowed_sections = get_allowed_sections(role)
            view_only_sections = []

    return {
        'allowed_sections': allowed_sections,
        'view_only_sections': view_only_sections,
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
            'communications': CommunicationLog.objects.count(),
            'tickets_open': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
            'tickets_critical': Ticket.objects.filter(priority='critical', status__in=['open', 'in_progress']).count(),
            'activity_today': ActivityLog.objects.filter(created_at__date=today).count(),
            'contracts_active': Contract.objects.filter(status__in=['active', 'signed']).count(),
            'contracts_draft': Contract.objects.filter(status='draft').count(),
            'documents': Document.objects.count(),
            'unread_notifications': Notification.objects.filter(
                user=request.user, is_read=False
            ).count(),
        }
    }
