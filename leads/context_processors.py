from django.utils import timezone
from .models import Lead, FollowUp

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
            'followup_pending': followups.filter(status='pending').count(),
            'followup_today': followups.filter(status='pending', follow_up_date__date=today).count(),
            'followup_next': followups.filter(status='pending', follow_up_date__date__gt=today).count(),
            'followup_done': followups.filter(status='done').count(),
        }
    }