from datetime import timedelta
from django.db.models import Sum, F, Count
from django.utils import timezone
from leads.models import Lead, FollowUp, Quotation, Meeting, SalesPerson, GeneralTask

TOOL_REGISTRY = {}

def register_tool(name, requires_action=False):
    def decorator(fn):
        TOOL_REGISTRY[name] = {'fn': fn, 'requires_action': requires_action}
        return fn
    return decorator


def _get_salesperson(user):
    """Map the logged-in Django User to their SalesPerson record, if any."""
    return SalesPerson.objects.filter(user=user).first()


@register_tool('show_hot_leads')
def show_hot_leads(user, assistant_type, params):
    qs = Lead.objects.exclude(ai_score__isnull=True).order_by('-ai_score')
    if assistant_type == 'sales':
        sp = _get_salesperson(user)
        if not sp:
            return {'error': 'Your account is not linked to a salesperson profile, so I can only answer questions about the CRM as a whole via the CRM Assistant.'}
        qs = qs.filter(spo=sp)
    return {'leads': list(qs.values('id', 'name', 'contact_number', 'status', 'ai_score')[:20])}


@register_tool('show_pending_tasks')
def show_pending_tasks(user, assistant_type, params):
    qs = FollowUp.objects.filter(status='pending').select_related('lead')
    if assistant_type == 'sales':
        sp = _get_salesperson(user)
        if not sp:
            return {'error': 'Your account is not linked to a salesperson profile, so I can only answer questions about the CRM as a whole via the CRM Assistant.'}
        qs = qs.filter(spo=sp)
    return {'followups': [
        {'lead': f.lead.name, 'date': f.follow_up_date.isoformat(), 'notes': f.notes}
        for f in qs[:20]
    ]}


@register_tool('show_today_meetings')
def show_today_meetings(user, assistant_type, params):
    today = timezone.localdate()
    qs = Meeting.objects.filter(scheduled_at__date=today)
    if assistant_type == 'sales':
        sp = _get_salesperson(user)
        if not sp:
            return {'error': 'Your account is not linked to a salesperson profile.'}
        qs = qs.filter(lead__spo=sp)
    return {'meetings': list(qs.values('id', 'title', 'scheduled_at', 'lead__name')[:20])}


@register_tool('show_best_salesperson')
def show_best_salesperson(user, assistant_type, params):
    if assistant_type != 'crm':
        return {'error': 'Not permitted for sales assistant'}
    top = (Lead.objects.filter(status='converted')
           .values('spo__name')
           .annotate(total=Count('id'))
           .order_by('-total')[:5])
    return {'ranking': list(top)}


@register_tool('show_quotations_above')
def show_quotations_above(user, assistant_type, params):
    amount = params.get('amount', 500000)
    qs = Quotation.objects.annotate(
        total_amount=Sum(F('items__quantity') * F('items__unit_price'))
    ).filter(total_amount__gte=amount)
    if assistant_type == 'sales':
        sp = _get_salesperson(user)
        if not sp:
            return {'error': 'Your account is not linked to a salesperson profile, so I can only answer questions about the CRM as a whole via the CRM Assistant.'}
        qs = qs.filter(spo=sp)
    return {'quotations': list(qs.values('id', 'lead__name', 'total_amount')[:20])}


@register_tool('create_followup', requires_action=True)
def create_followup(user, assistant_type, params):
    lead_id = params.get('lead_id')
    days_from_now = params.get('days_from_now', 1)
    notes = params.get('notes', '')
    lead = Lead.objects.get(id=lead_id)
    if assistant_type == 'sales':
        sp = _get_salesperson(user)
        if not sp or lead.spo_id != sp.id:
            return {'error': 'Not your lead'}
    followup = FollowUp.objects.create(
        lead=lead,
        follow_up_date=timezone.now() + timedelta(days=days_from_now),
        notes=notes,
        status='pending'
    )
    return {'created': True, 'followup_id': followup.id}


@register_tool('create_meeting', requires_action=True)
def create_meeting(user, assistant_type, params):
    lead = Lead.objects.get(id=params['lead_id'])
    if assistant_type == 'sales':
        sp = _get_salesperson(user)
        if not sp or lead.spo_id != sp.id:
            return {'error': 'Not your lead'}
    meeting = Meeting.objects.create(
        lead=lead,
        title=params.get('title', f'Meeting with {lead.name}'),
        scheduled_at=params.get('scheduled_at', timezone.now()),
        created_by=user,
    )
    return {'created': True, 'meeting_id': meeting.id}


@register_tool('create_quotation', requires_action=True)
def create_quotation(user, assistant_type, params):
    lead = Lead.objects.get(id=params['lead_id'])
    if assistant_type == 'sales':
        sp = _get_salesperson(user)
        if not sp or lead.spo_id != sp.id:
            return {'error': 'Not your lead'}
    quotation = Quotation.objects.create(
        lead=lead,
        created_by=user,
    )
    return {'created': True, 'quotation_id': quotation.id}


@register_tool('search_leads_by_name')
def search_leads_by_name(user, assistant_type, params):
    name = params.get('name', '').strip()
    if not name:
        return {'error': 'No name provided to search for.'}

    qs = Lead.objects.filter(name__icontains=name)
    if assistant_type == 'sales':
        sp = _get_salesperson(user)
        if not sp:
            return {'error': 'Your account is not linked to a salesperson profile.'}
        qs = qs.filter(spo=sp)

    results = list(qs.values('id', 'name', 'contact_number', 'status')[:10])
    if not results:
        return {'leads': [], 'message': f'No leads found matching "{name}".'}
    return {'leads': results}


@register_tool('create_task', requires_action=True)
def create_task(user, assistant_type, params):
    title = params.get('title', '').strip()
    if not title:
        return {'error': 'A task title is required.'}

    lead_id = params.get('lead_id')
    lead = None
    if lead_id:
        lead = Lead.objects.filter(id=lead_id).first()
        if assistant_type == 'sales' and lead:
            sp = _get_salesperson(user)
            if not sp or lead.spo_id != sp.id:
                return {'error': 'Not your lead'}

    days_from_now = params.get('days_from_now')
    due_date = None
    if days_from_now is not None:
        due_date = (timezone.localdate() + timedelta(days=days_from_now))

    task = GeneralTask.objects.create(
        title=title,
        description=params.get('description', ''),
        assigned_to=user,
        created_by=user,
        priority=params.get('priority', 'medium'),
        due_date=due_date,
        lead=lead,
    )
    return {'created': True, 'task_id': task.id, 'title': task.title}


TOOL_SCHEMAS = {
    "show_hot_leads": {
        "type": "function",
        "function": {
            "name": "show_hot_leads",
            "description": "Get leads sorted by AI score (highest first) — the 'hottest' or most promising leads.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }
    },
    "show_pending_tasks": {
        "type": "function",
        "function": {
            "name": "show_pending_tasks",
            "description": "Get pending follow-up tasks that haven't been marked done yet.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }
    },
    "show_today_meetings": {
        "type": "function",
        "function": {
            "name": "show_today_meetings",
            "description": "Get meetings scheduled for today.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }
    },
    "show_best_salesperson": {
        "type": "function",
        "function": {
            "name": "show_best_salesperson",
            "description": "Get the ranking of salespeople by number of converted leads. CRM-wide only, not available to sales assistant.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }
    },
    "show_quotations_above": {
        "type": "function",
        "function": {
            "name": "show_quotations_above",
            "description": "Get quotations with total amount above a given threshold.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "Minimum quotation amount, e.g. 500000"}
                },
                "required": []
            },
        }
    },
    "create_followup": {
        "type": "function",
        "function": {
            "name": "create_followup",
            "description": "Create a new follow-up reminder for a specific lead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_id": {"type": "integer", "description": "The ID of the lead"},
                    "days_from_now": {"type": "integer", "description": "How many days from today, e.g. 1 for tomorrow"},
                    "notes": {"type": "string", "description": "Follow-up notes"}
                },
                "required": ["lead_id"]
            },
        }
    },
    "create_meeting": {
        "type": "function",
        "function": {
            "name": "create_meeting",
            "description": "Schedule a new meeting for a specific lead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_id": {"type": "integer", "description": "The ID of the lead"},
                    "title": {"type": "string", "description": "Meeting title"}
                },
                "required": ["lead_id"]
            },
        }
    },
    "create_quotation": {
        "type": "function",
        "function": {
            "name": "create_quotation",
            "description": "Create a new quotation for a specific lead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_id": {"type": "integer", "description": "The ID of the lead"}
                },
                "required": ["lead_id"]
            },
        }
    },
    "search_leads_by_name": {
        "type": "function",
        "function": {
            "name": "search_leads_by_name",
            "description": "Search for leads by name (partial match). Use this whenever the user refers to a lead by name instead of ID, before calling create_followup/create_meeting/create_quotation, to find the correct lead_id first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Full or partial lead name to search for"}
                },
                "required": ["name"]
            },
        }
    },
    "create_task": {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create a new general task (to-do), optionally linked to a lead. Use this when the user wants a task/to-do created, as distinct from a follow-up reminder or a meeting.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title, e.g. 'Prepare meeting notes'"},
                    "description": {"type": "string", "description": "Optional task details"},
                    "lead_id": {"type": "integer", "description": "Optional lead ID this task relates to"},
                    "days_from_now": {"type": "integer", "description": "Due date, as days from today, e.g. 3 for a task due in 3 days"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"], "description": "Task priority"}
                },
                "required": ["title"]
            },
        }
    },
}