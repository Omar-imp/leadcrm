from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout
from .forms import LeadForm, FollowUpForm, PaymentForm, ScheduledPaymentForm, InstallmentForm
from django.contrib.auth.models import User
from .decorators import role_required
from django.db.models import Sum, Count
import csv
import io
import openpyxl
from .ai_assignment import assign_lead_with_ai
from .duplicate_detector import check_and_mark_duplicate
from .ai_scorer import update_lead_score
from .ai_next_action import get_next_action
from .ai_closing import update_closing_probability
from .ai_followup_messages import generate_followup_message
from .ai_meeting_summary import save_meeting_summary
from .ai_forecasting import generate_sales_forecast
from .ai_churn import update_churn_risk, get_high_churn_leads
from .ai_upsell import get_upsell_recommendations
from .ai_ltv import update_lifetime_value
from .ai_forecasting import generate_sales_forecast
from .ai_churn import get_high_churn_leads
from django.views.decorators.http import require_POST
from .decorators import role_required, block_view_only
from .models import (Lead, FollowUp, SalesPerson, Payment,
                     ScheduledPayment, Installment, UserProfile,
                     Company, Contact, Opportunity,
                     Quotation, QuotationItem,
                     Project, Milestone, Task,
                     Meeting, GeneralTask, CommunicationLog,
                     Ticket, TicketReply, ActivityLog, Document,
                     Contract, Notification,
                     LEAD_SOURCE_CHOICES, OPPORTUNITY_STAGE_CHOICES, PRIORITY_CHOICES,
                     QUOTATION_STATUS_CHOICES,
                     PROJECT_STATUS_CHOICES, PROJECT_PRIORITY_CHOICES,
                     METHODOLOGY_CHOICES, MILESTONE_STATUS_CHOICES,
                     TASK_STATUS_CHOICES, TASK_PRIORITY_CHOICES,
                     MEETING_STATUS_CHOICES, MEETING_TYPE_CHOICES,
                     GENERAL_TASK_STATUS_CHOICES, GENERAL_TASK_PRIORITY_CHOICES,
                     COMMUNICATION_TYPE_CHOICES, COMMUNICATION_DIRECTION_CHOICES,
                     TICKET_STATUS_CHOICES, TICKET_PRIORITY_CHOICES,
                     TICKET_CATEGORY_CHOICES, DOCUMENT_TYPE_CHOICES, CONTRACT_STATUS_CHOICES)


def create_notification(user, notif_type, title, message, link=None):
    Notification.objects.create(
        user=user,
        notif_type=notif_type,
        title=title,
        message=message,
        link=link,
    )


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'leads/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    leads = Lead.objects.all()
    today = timezone.localdate()

    stats = {
        'total': leads.count(),
        'new': leads.filter(status='new').count(),
        'positive': leads.filter(status='positive').count(),
        'lost': leads.filter(status='lost').count(),
        'quotation': leads.filter(status='quotation').count(),
        'convert': leads.filter(status='converted').count(),
    }

    followups = FollowUp.objects.all()
    followup_stats = {
        'today': followups.filter(status='pending', follow_up_date__date=today).count(),
        'next': followups.filter(status='pending', follow_up_date__date__gt=today).count(),
        'pending': followups.filter(status='pending').count(),
        'done': followups.filter(status='done').count(),
    }

    spo_rows = []
    for spo in SalesPerson.objects.all():
        spo_leads = Lead.objects.filter(spo=spo)
        spo_rows.append({
            'name': spo.name,
            'total': spo_leads.count(),
            'new': spo_leads.filter(status='new').count(),
            'assign': spo_leads.exclude(status='new').count(),
            'positive': spo_leads.filter(status='positive').count(),
            'lost': spo_leads.filter(status='lost').count(),
            'quotation': spo_leads.filter(status='quotation').count(),
            'convert': spo_leads.filter(status='converted').count(),
        })

    context = {
        'stats': stats,
        'followup_stats': followup_stats,
        'spo_rows': spo_rows,
        'active': 'dashboard',
    }
    return render(request, 'leads/dashboard.html', context)


@login_required
@block_view_only
def create_lead(request):
    if request.method == 'POST':
        form = LeadForm(request.POST)
        if form.is_valid():
            lead = form.save(commit=False)
            if hasattr(request.user, 'salesperson'):
                lead.spo = request.user.salesperson
            lead.save()
            is_dup = check_and_mark_duplicate(lead)
            if is_dup:
                messages.warning(
                    request,
                    f'Warning: This lead may be a duplicate of an existing lead.'
                )
            else:
                assigned = assign_lead_with_ai(lead)
                if assigned:
                    messages.info(
                        request,
                        f'Lead auto-assigned to {lead.spo.name} by AI'
                    )
            _send_whatsapp_welcome(lead)
            messages.success(request, 'Lead created successfully.')
            return redirect('all_leads')
    else:
        form = LeadForm()
    spo_name = None
    if hasattr(request.user, 'salesperson'):
        spo_name = request.user.salesperson.name
    return render(request, 'leads/lead_form.html', {
        'form': form,
        'active': 'create_lead',
        'spo_name': spo_name,
    })


@login_required
def lead_delete(request, pk):
    lead = get_object_or_404(Lead, pk=pk)

    lead_name = lead.name
    lead.delete()

    messages.success(request, f'Lead "{lead_name}" deleted successfully.')
    return redirect('all_leads')

    
def _send_whatsapp_welcome(lead):
    """
    Sends WhatsApp welcome message to a newly created lead.
    Never raises — failure is logged but does not break lead creation.
    """
    try:
        from chatbot.services.whatsapp import send_welcome_message
        from chatbot.models import ChatSession, ChatMessage

        success, result = send_welcome_message(
            name=lead.name,
            phone=lead.contact_number,
        )

        # create a chat session for this lead
        if success:
            from chatbot.services.utils import normalize_phone
            from chatbot.services.prompts import WELCOME_MESSAGE_TEMPLATE

            normalized = normalize_phone(lead.contact_number)
            session, _ = ChatSession.objects.get_or_create(
                phone_number=normalized,
                defaults={'lead_name': lead.name}
            )
            if not session.lead_name:
                session.lead_name = lead.name
                session.save(update_fields=['lead_name'])

            welcome_text = WELCOME_MESSAGE_TEMPLATE.format(name=lead.name)
            ChatMessage.objects.create(
                session=session,
                direction='outbound',
                message=welcome_text,
                whatsapp_message_id=result,
                delivered=True,
            )
            import logging
            logging.getLogger(__name__).info(
                'Welcome message sent to lead #%s (%s)', lead.pk, lead.name
            )
        else:
            import logging
            logging.getLogger(__name__).warning(
                'Welcome message failed for lead #%s: %s', lead.pk, result
            )

    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception(
            'WhatsApp welcome error for lead #%s: %s', lead.pk, exc
        )


@login_required
def bulk_whatsapp_sender(request):
    """
    Upload an Excel file containing Name and Phone columns.
    Sends a welcome WhatsApp message to every number in the file.
    Does NOT create leads — purely for sending messages.
    """
    if request.method == 'POST':
        file = request.FILES.get('file')
        if not file:
            messages.error(request, 'Please select an Excel file.')
            return redirect('bulk_whatsapp_sender')

        try:
            import openpyxl
            wb = openpyxl.load_workbook(file, data_only=True)
            ws = wb.active
            headers = [
                str(cell.value).strip().lower() if cell.value else ''
                for cell in ws[1]
            ]
        except Exception as e:
            messages.error(request, f'Could not read file: {e}')
            return redirect('bulk_whatsapp_sender')

        from chatbot.services.whatsapp import send_welcome_message

        sent = 0
        failed = 0
        errors = []

        for row in ws.iter_rows(min_row=2, values_only=True):
            row_dict = dict(zip(headers, row))

            name = str(row_dict.get('name', '') or '').strip()
            phone = str(
                row_dict.get('phone') or
                row_dict.get('contact_number') or
                row_dict.get('number') or ''
            ).strip()

            if not name or not phone:
                failed += 1
                continue

            success, result = send_welcome_message(name=name, phone=phone)
            if success:
                sent += 1
            else:
                failed += 1
                errors.append(f'{name} ({phone}): {result}')

        if sent:
            messages.success(request, f'{sent} messages sent successfully.')
        if failed:
            messages.error(
                request,
                f'{failed} failed. ' + ' | '.join(errors[:5])
            )

        return redirect('bulk_whatsapp_sender')

    return render(request, 'leads/bulk_whatsapp_sender.html', {
        'active': 'bulk_whatsapp',
        'title': 'Bulk WhatsApp Sender',
    })


@login_required
def ai_assign_lead(request, pk):
    """Manually trigger AI assignment for a lead."""
    lead = get_object_or_404(Lead, pk=pk)
    success = assign_lead_with_ai(lead)
    if success:
        messages.success(request, f'Lead assigned to {lead.spo.name} by AI.')
    else:
        messages.error(request, 'AI assignment failed. No salespersons available.')
    return redirect('lead_detail', pk=pk)


@login_required
@block_view_only
def bulk_import_leads(request):
    if request.method == 'POST':
        file = request.FILES.get('import_file')
        if not file:
            messages.error(request, 'Please select a CSV or Excel file.')
            return redirect('create_lead')

        filename = file.name.lower()
        rows = []

        try:
            if filename.endswith('.csv'):
                decoded = file.read().decode('utf-8-sig')
                reader = csv.DictReader(io.StringIO(decoded))
                rows = list(reader)
            elif filename.endswith('.xlsx') or filename.endswith('.xls'):
                wb = openpyxl.load_workbook(file, data_only=True)
                ws = wb.active
                headers = [str(cell.value).strip() if cell.value else '' for cell in ws[1]]
                for row in ws.iter_rows(min_row=2, values_only=True):
                    row_dict = dict(zip(headers, row))
                    rows.append(row_dict)
            else:
                messages.error(request, 'Unsupported file type. Please upload a .csv or .xlsx file.')
                return redirect('create_lead')
        except Exception as e:
            messages.error(request, f'Could not read the file: {e}')
            return redirect('create_lead')

        valid_sources = dict(LEAD_SOURCE_CHOICES)
        spo = request.user.salesperson if hasattr(request.user, 'salesperson') else None

        created_count = 0
        skipped_count = 0
        errors = []

        for i, row in enumerate(rows, start=2):
            # normalize keys to lowercase, no spaces, for flexible header matching
            normalized = {
                str(k).strip().lower().replace(' ', '_'): v
                for k, v in row.items() if k
            }

            name = str(normalized.get('name', '')).strip()
            contact_number = str(normalized.get('contact_number')
                                  or normalized.get('phone')
                                  or normalized.get('contact') or '').strip()
            email = str(normalized.get('email', '')).strip()
            city = str(normalized.get('city', '')).strip()
            country = str(normalized.get('country', '')).strip()
            address = str(normalized.get('address', '')).strip()
            detail = str(normalized.get('detail') or normalized.get('notes') or '').strip()
            quotation = normalized.get('quotation') or 0

            source_raw = str(normalized.get('lead_source') or normalized.get('source') or '').strip().lower()
            lead_source = 'advertisement'
            for key, label in LEAD_SOURCE_CHOICES:
                if source_raw == key or source_raw == label.lower():
                    lead_source = key
                    break

            if not name or not contact_number:
                skipped_count += 1
                errors.append(f'Row {i}: missing name or contact number, skipped.')
                continue

            try:
                lead = Lead.objects.create(
                    name=name,
                    contact_number=contact_number,
                    email=email or None,
                    city=city or None,
                    country=country or None,
                    address=address or None,
                    detail=detail or None,
                    quotation=quotation or 0,
                    lead_source=lead_source,
                    spo=spo,
                )
                check_and_mark_duplicate(lead)
                _send_whatsapp_welcome(lead)
                created_count += 1
            except Exception as e:
                skipped_count += 1
                errors.append(f'Row {i}: {e}')

        if created_count:
            messages.success(request, f'{created_count} leads imported successfully.')
        if skipped_count:
            messages.error(request, f'{skipped_count} rows skipped. ' + ' '.join(errors[:5]))

        return redirect('all_leads')

    return redirect('create_lead')


@login_required
def lead_list(request, status=None):
    leads = Lead.objects.all()
    title = 'All Leads'
    active = 'all_leads'
    if status:
        leads = leads.filter(status=status)
        title = dict(Lead._meta.get_field('status').choices).get(status, status.title())
        active = status

    q = request.GET.get('q')
    if q:
        leads = leads.filter(Q(name__icontains=q) | Q(contact_number__icontains=q) | Q(email__icontains=q))

    context = {'leads': leads, 'title': title, 'active': active}
    return render(request, 'leads/lead_list.html', context)


@login_required
@block_view_only
def update_lead_status(request, pk, status):
    lead = get_object_or_404(Lead, pk=pk)
    valid_statuses = dict(Lead._meta.get_field('status').choices)
    if status in valid_statuses:
        lead.status = status
        lead.save()
        messages.success(request, f'Lead marked as {valid_statuses[status]}.')
    return redirect(request.META.get('HTTP_REFERER', 'all_leads'))


@login_required
@block_view_only
def lead_detail(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    followup_form = FollowUpForm()

    if request.method == 'POST':
        followup_form = FollowUpForm(request.POST)
        if followup_form.is_valid():
            fu = followup_form.save(commit=False)
            fu.lead = lead
            fu.save()
            messages.success(request, 'Follow-up scheduled.')
            return redirect('lead_detail', pk=pk)

    # get AI next action
    next_action = request.session.get(f'next_action_{pk}')

    if not next_action and lead.ai_score_updated:
        next_action = get_next_action(lead)

    context = {
        'lead': lead,
        'followup_form': followup_form,
        'followups': lead.followups.all(),
        'active': 'all_leads',
        'next_action': next_action,
    }
    return render(request, 'leads/lead_detail.html', context)


@login_required
def next_action_view(request, pk):
    """Get AI next action recommendation for a lead."""
    lead = get_object_or_404(Lead, pk=pk)
    next_action = get_next_action(lead)
    request.session[f'next_action_{pk}'] = next_action
    messages.success(
        request,
        f'Next Action: {next_action["action"]} — {next_action["deadline"]}'
    )
    return redirect('lead_detail', pk=pk)


@login_required
@block_view_only
def followup_done(request, pk):
    followup = get_object_or_404(FollowUp, pk=pk)
    followup.status = 'done'
    followup.save()
    messages.success(request, 'Follow-up marked done.')
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


@login_required
def followup_list(request, scope):
    today = timezone.localdate()
    followups = FollowUp.objects.select_related('lead').all()
    title = 'Follow Ups'
    if scope == 'pending':
        followups = followups.filter(status='pending')
        title = 'Pending Follow Ups'
    elif scope == 'today':
        followups = followups.filter(status='pending', follow_up_date__date=today)
        title = "Today's Follow Ups"
    elif scope == 'next':
        followups = followups.filter(status='pending', follow_up_date__date__gt=today)
        title = 'Next Follow Ups'
    elif scope == 'done':
        followups = followups.filter(status='done')
        title = 'Done Follow Ups'

    context = {'followups': followups, 'title': title, 'active': scope}
    return render(request, 'leads/followup_list.html', context)

@login_required
def payment_list(request, ptype):
    payments = Payment.objects.select_related('lead').filter(payment_type=ptype)
    title = 'Advance Payments' if ptype == 'advance' else 'Full Payments'
    context = {'payments': payments, 'title': title, 'active': ptype}
    return render(request, 'leads/payment_list.html', context)


@login_required
@block_view_only
def add_payment(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.lead = lead
            payment.save()
            messages.success(request, 'Payment recorded.')
    return redirect('lead_detail', pk=pk)


@login_required
def scheduled_payment_list(request):
    schedules = ScheduledPayment.objects.select_related('lead').all()
    context = {'schedules': schedules, 'title': 'Scheduled Payments', 'active': 'scheduled'}
    return render(request, 'leads/scheduled_payment_list.html', context)


@login_required
@block_view_only
def scheduled_payment_create(request):
    if request.method == 'POST':
        form = ScheduledPaymentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Payment plan created.')
            return redirect('scheduled_payment_list')
    else:
        form = ScheduledPaymentForm()
    context = {'form': form, 'title': 'Create Payment Plan', 'active': 'scheduled'}
    return render(request, 'leads/scheduled_payment_form.html', context)


@login_required
@block_view_only
def scheduled_payment_detail(request, pk):
    schedule = get_object_or_404(ScheduledPayment, pk=pk)
    installment_form = InstallmentForm()

    if request.method == 'POST':
        if 'add_installment' in request.POST:
            installment_form = InstallmentForm(request.POST)
            if installment_form.is_valid():
                installment = installment_form.save(commit=False)
                installment.schedule = schedule
                installment.save()
                messages.success(request, 'Installment added.')
                return redirect('scheduled_payment_detail', pk=pk)
        elif 'mark_paid' in request.POST:
            installment_id = request.POST.get('installment_id')
            installment = get_object_or_404(Installment, pk=installment_id, schedule=schedule)
            installment.is_paid = True
            installment.paid_date = timezone.localdate()
            installment.save()
            messages.success(request, 'Installment marked as paid.')
            return redirect('scheduled_payment_detail', pk=pk)

    context = {
        'schedule': schedule,
        'installments': schedule.installments.all(),
        'installment_form': installment_form,
        'active': 'scheduled',
    }
    return render(request, 'leads/scheduled_payment_detail.html', context)

SECTION_LABELS = {
    'dashboard': 'Dashboard',
    'leads': 'Leads',
    'contacts': 'Contacts & Companies',
    'pipeline': 'Pipeline & Opportunities',
    'quotations': 'Quotations',
    'projects': 'Projects',
    'meetings': 'Meetings',
    'tasks': 'Tasks',
    'payments': 'Payments',
    'followups': 'Follow Ups',
    'communications': 'Communications',
    'support': 'Support Tickets',
    'activity': 'Activity Logs',
    'reports': 'Reports & Analytics',
    'documents': 'Documents',
    'contracts': 'Contracts',
    'salespersons': 'Sales Persons',
    'users': 'User Management',
    'ceo_dashboard': 'CEO Dashboard',
    'whatsapp': 'WhatsApp Sender',
}


@login_required
@role_required('admin')
def user_list(request):
    users = User.objects.select_related('profile').all().order_by('username')
    context = {'users': users, 'active': 'users', 'title': 'Users'}
    return render(request, 'leads/user_list.html', context)


@login_required
@role_required('admin')
def user_create(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')
        phone = request.POST.get('phone')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        else:
            user = User.objects.create_user(
                username=username, email=email, password=password
            )
            user.profile.role = role
            user.profile.phone = phone
            user.profile.save()

            # save custom permissions
            _save_user_permissions(user, request.POST)

            messages.success(request, f'User {username} created.')
            return redirect('user_list')

    from .models import ROLE_CHOICES
    return render(request, 'leads/user_form.html', {
        'active': 'users',
        'title': 'Create User',
        'role_choices': ROLE_CHOICES,
        'section_labels': SECTION_LABELS,
        'permission_choices': ['full', 'view', 'none'],
    })


@login_required
@role_required('admin')
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        user.email = request.POST.get('email')
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.save()
        user.profile.role = request.POST.get('role')
        user.profile.phone = request.POST.get('phone')
        user.profile.save()

        # save custom permissions
        _save_user_permissions(user, request.POST)

        messages.success(request, 'User updated.')
        return redirect('user_list')

    from .models import ROLE_CHOICES
    # get current permissions
    try:
        perms = user.custom_permissions
    except Exception:
        from .models import UserPermissions
        perms, _ = UserPermissions.objects.get_or_create(user=user)

    return render(request, 'leads/user_form.html', {
        'active': 'users',
        'title': 'Edit User',
        'edit_user': user,
        'role_choices': ROLE_CHOICES,
        'section_labels': SECTION_LABELS,
        'permission_choices': ['full', 'view', 'none'],
        'current_perms': perms,
    })


def _save_user_permissions(user, post_data):
    """Saves custom section permissions from form POST data."""
    from .models import UserPermissions
    perms, _ = UserPermissions.objects.get_or_create(user=user)

    for section in UserPermissions.ALL_SECTIONS:
        value = post_data.get(f'perm_{section}', 'none')
        if value in ['full', 'view', 'none']:
            setattr(perms, section, value)

    perms.save()


@login_required
@role_required('admin')
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "You can't delete your own account.")
    else:
        user.delete()
        messages.success(request, 'User deleted.')
    return redirect('user_list')

# ── COMPANY VIEWS ──────────────────────────────────────────

@login_required
def company_list(request):
    q = request.GET.get('q')
    companies = Company.objects.all()
    if q:
        companies = companies.filter(
            Q(name__icontains=q) | Q(email__icontains=q) | Q(city__icontains=q)
        )
    context = {'companies': companies, 'active': 'companies', 'title': 'Companies'}
    return render(request, 'leads/company_list.html', context)

@login_required
@block_view_only
def company_create(request):
    if request.method == 'POST':
        company = Company(
            name     = request.POST.get('name'),
            industry = request.POST.get('industry'),
            website  = request.POST.get('website') or None,
            email    = request.POST.get('email') or None,
            phone    = request.POST.get('phone'),
            address  = request.POST.get('address'),
            city     = request.POST.get('city'),
            country  = request.POST.get('country'),
            notes    = request.POST.get('notes'),
        )
        company.save()
        messages.success(request, f'Company "{company.name}" created.')
        return redirect('company_list')
    from .models import INDUSTRY_CHOICES
    return render(request, 'leads/company_form.html', {
        'active'          : 'companies',
        'title'           : 'Add Company',
        'industry_choices': INDUSTRY_CHOICES,
    })

@login_required
@block_view_only
def company_edit(request, pk):
    company = get_object_or_404(Company, pk=pk)
    if request.method == 'POST':
        company.name     = request.POST.get('name')
        company.industry = request.POST.get('industry')
        company.website  = request.POST.get('website') or None
        company.email    = request.POST.get('email') or None
        company.phone    = request.POST.get('phone')
        company.address  = request.POST.get('address')
        company.city     = request.POST.get('city')
        company.country  = request.POST.get('country')
        company.notes    = request.POST.get('notes')
        company.save()
        messages.success(request, 'Company updated.')
        return redirect('company_list')
    from .models import INDUSTRY_CHOICES
    return render(request, 'leads/company_form.html', {
        'active' : 'companies',
        'title'  : 'Edit Company',
        'company': company,
        'industry_choices': INDUSTRY_CHOICES,
    })

@login_required
@block_view_only
def company_delete(request, pk):
    company = get_object_or_404(Company, pk=pk)
    company.delete()
    messages.success(request, 'Company deleted.')
    return redirect('company_list')

@login_required
def company_detail(request, pk):
    company  = get_object_or_404(Company, pk=pk)
    contacts = company.contacts.all()
    context  = {'company': company, 'contacts': contacts, 'active': 'companies'}
    return render(request, 'leads/company_detail.html', context)

# ── CONTACT VIEWS ──────────────────────────────────────────

def contact_list(request):
    q = request.GET.get('q')
    contacts = Contact.objects.select_related('company').all()
    if q:
        contacts = contacts.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) |
            Q(email__icontains=q) | Q(phone__icontains=q)
        )
    context = {'contacts': contacts, 'active': 'contacts', 'title': 'Contacts'}
    return render(request, 'leads/contact_list.html', context)

@login_required
@block_view_only
def contact_create(request):
    if request.method == 'POST':
        company_id = request.POST.get('company')
        lead_id    = request.POST.get('lead')
        contact    = Contact(
            first_name = request.POST.get('first_name'),
            last_name  = request.POST.get('last_name') or None,
            email      = request.POST.get('email') or None,
            phone      = request.POST.get('phone'),
            job_title  = request.POST.get('job_title'),
            company_id = company_id if company_id else None,
            lead_id    = lead_id if lead_id else None,
            notes      = request.POST.get('notes'),
        )
        contact.save()
        messages.success(request, 'COntact created.')
        return redirect('contact_list')
    return render(request, 'leads/contact_form.html', {
        'active'   : 'contacts',
        'title'    : 'Add Contacts',
        'companies': Company.objects.all(),
        'leads'    : Lead.objects.all(),
    })

@login_required
@block_view_only
def contact_edit(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    if request.method == 'POST':
        company_id         = request.POST.get('company')
        lead_id            = request.POST.get('lead')
        contact.first_name = request.POST.get('first_name')
        contact.last_name  = request.POST.get('last_name') or None
        contact.email      = request.POST.get('email') or None
        contact.phone      = request.POST.get('phone')
        contact.company_id = company_id if company_id else None
        contact.lead_id    = lead_id if lead_id else None
        contact.notes      = request.POST.get('notes')
        contact.save()
        messages.success(request, 'Contact updated.')
        return redirect('contact_list')
    return render(request, 'leads/contact_form.html', {
        'active'   : 'contacts',
        'title'    : 'Edit Contact',
        'contact'  : contact,
        'companies': Company.objects.all(),
        'leads'    : Lead.objects.all(),
    })

@login_required
@block_view_only
def contact_delete(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    contact.delete()
    messages.success(request, 'Contact deleted.')
    return redirect('contact_list')

# ── OPPORTUNITY VIEWS ──────────────────────────────────────

@login_required
def opportunity_pipeline(request):
    """Kanban pipeline view — one column per stage."""
    stages = OPPORTUNITY_STAGE_CHOICES
    pipeline = {}
    for stage_key, stage_label in stages:
        opps = Opportunity.objects.filter(stage=stage_key).select_related(
            'lead', 'contact', 'company', 'assigned_to'
        )
        pipeline[stage_key] = {
            'label': stage_label,
            'opps': opps,
            'count': opps.count(),
            'total': sum(o.value for o in opps),
        }
    context = {
        'pipeline': pipeline,
        'stages': stages,
        'active': 'pipeline',
        'title': 'Sales Pipeline',
    }
    return render(request, 'leads/pipeline.html', context)


@login_required
def opportunity_list(request):
    opps = Opportunity.objects.select_related(
        'lead', 'contact', 'company', 'assigned_to'
    ).all()
    q = request.GET.get('q')
    if q:
        opps = opps.filter(Q(title__icontains=q) | Q(company__name__icontains=q))
    stage = request.GET.get('stage')
    if stage:
        opps = opps.filter(stage=stage)
    context = {
        'opps': opps,
        'active': 'opportunities',
        'title': 'All Opportunities',
        'stages': OPPORTUNITY_STAGE_CHOICES,
        'selected_stage': stage,
    }
    return render(request, 'leads/opportunity_list.html', context)


@login_required
@block_view_only
def opportunity_create(request):
    if request.method == 'POST':
        opp = Opportunity(
            title=request.POST.get('title'),
            stage=request.POST.get('stage', 'new'),
            priority=request.POST.get('priority', 'medium'),
            value=request.POST.get('value') or 0,
            probability=request.POST.get('probability') or 0,
            description=request.POST.get('description'),
            expected_close_date=request.POST.get('expected_close_date') or None,
        )
        lead_id = request.POST.get('lead')
        contact_id = request.POST.get('contact')
        company_id = request.POST.get('company')
        assigned_id = request.POST.get('assigned_to')
        if lead_id:
            opp.lead_id = lead_id
        if contact_id:
            opp.contact_id = contact_id
        if company_id:
            opp.company_id = company_id
        if assigned_id:
            opp.assigned_to_id = assigned_id
        opp.save()
        messages.success(request, f'Opportunity "{opp.title}" created.')
        return redirect('opportunity_pipeline')
    context = {
        'active': 'pipeline',
        'title': 'Create Opportunity',
        'stages': OPPORTUNITY_STAGE_CHOICES,
        'priorities': PRIORITY_CHOICES,
        'leads': Lead.objects.all(),
        'contacts': Contact.objects.all(),
        'companies': Company.objects.all(),
        'users': User.objects.all(),
    }
    return render(request, 'leads/opportunity_form.html', context)


@login_required
def opportunity_detail(request, pk):
    opp = get_object_or_404(Opportunity, pk=pk)
    context = {
        'opp': opp,
        'active': 'pipeline',
        'stages': OPPORTUNITY_STAGE_CHOICES,
    }
    return render(request, 'leads/opportunity_detail.html', context)


@login_required
@block_view_only
def opportunity_edit(request, pk):
    opp = get_object_or_404(Opportunity, pk=pk)
    if request.method == 'POST':
        opp.title = request.POST.get('title')
        opp.stage = request.POST.get('stage', 'new')
        opp.priority = request.POST.get('priority', 'medium')
        opp.value = request.POST.get('value') or 0
        opp.probability = request.POST.get('probability') or 0
        opp.description = request.POST.get('description')
        opp.expected_close_date = request.POST.get('expected_close_date') or None
        opp.lost_reason = request.POST.get('lost_reason') or None
        lead_id = request.POST.get('lead')
        contact_id = request.POST.get('contact')
        company_id = request.POST.get('company')
        assigned_id = request.POST.get('assigned_to')
        opp.lead_id = lead_id if lead_id else None
        opp.contact_id = contact_id if contact_id else None
        opp.company_id = company_id if company_id else None
        opp.assigned_to_id = assigned_id if assigned_id else None
        opp.save()
        messages.success(request, 'Opportunity updated.')
        return redirect('opportunity_detail', pk=pk)
    context = {
        'active': 'pipeline',
        'title': 'Edit Opportunity',
        'opp': opp,
        'stages': OPPORTUNITY_STAGE_CHOICES,
        'priorities': PRIORITY_CHOICES,
        'leads': Lead.objects.all(),
        'contacts': Contact.objects.all(),
        'companies': Company.objects.all(),
        'users': User.objects.all(),
    }
    return render(request, 'leads/opportunity_form.html', context)


@login_required
@block_view_only
def opportunity_delete(request, pk):
    opp = get_object_or_404(Opportunity, pk=pk)
    opp.delete()
    messages.success(request, 'Opportunity deleted.')
    return redirect('opportunity_pipeline')


@login_required
@block_view_only
def opportunity_move(request, pk, stage):
    """Quick stage move — called from pipeline card buttons."""
    opp = get_object_or_404(Opportunity, pk=pk)
    valid = dict(OPPORTUNITY_STAGE_CHOICES)
    if stage in valid:
        opp.stage = stage
        if stage == 'won':
            opp.probability = 100
        elif stage == 'lost':
            opp.probability = 0
        opp.save()
        messages.success(request, f'Moved to {valid[stage]}.')
    return redirect(request.META.get('HTTP_REFERER', 'opportunity_pipeline'))

# ── QUOTATION VIEWS ────────────────────────────────────────

@login_required
def quotation_list(request):
    quotations = Quotation.objects.select_related(
        'opportunity', 'company', 'contact', 'created_by'
    ).all()
    q = request.GET.get('q')
    if q:
        quotations = quotations.filter(
            Q(title__icontains=q) | Q(company__name__icontains=q)
        )
    status = request.GET.get('status')
    if status:
        quotations = quotations.filter(status=status)
    context = {
        'quotations': quotations,
        'active': 'quotations',
        'title': 'Quotations',
        'status_choices': QUOTATION_STATUS_CHOICES,
        'selected_status': status,
    }
    return render(request, 'leads/quotation_list.html', context)


@login_required
@block_view_only
def quotation_create(request):
    if request.method == 'POST':
        quotation = Quotation(
            title=request.POST.get('title'),
            status=request.POST.get('status', 'draft'),
            valid_until=request.POST.get('valid_until') or None,
            notes=request.POST.get('notes'),
            terms=request.POST.get('terms'),
            created_by=request.user,
        )
        opp_id = request.POST.get('opportunity')
        lead_id = request.POST.get('lead')
        company_id = request.POST.get('company')
        contact_id = request.POST.get('contact')
        if opp_id:
            quotation.opportunity_id = opp_id
        if lead_id:
            quotation.lead_id = lead_id
        if company_id:
            quotation.company_id = company_id
        if contact_id:
            quotation.contact_id = contact_id
        quotation.save()

        # save line items
        descriptions = request.POST.getlist('description')
        quantities = request.POST.getlist('quantity')
        unit_prices = request.POST.getlist('unit_price')
        for desc, qty, price in zip(descriptions, quantities, unit_prices):
            if desc.strip():
                QuotationItem.objects.create(
                    quotation=quotation,
                    description=desc,
                    quantity=qty or 1,
                    unit_price=price or 0,
                )

        messages.success(request, f'Quotation "{quotation.title}" created.')
        return redirect('quotation_detail', pk=quotation.pk)

    context = {
        'active': 'quotations',
        'title': 'Create Quotation',
        'status_choices': QUOTATION_STATUS_CHOICES,
        'opportunities': Opportunity.objects.all(),
        'leads': Lead.objects.all(),
        'companies': Company.objects.all(),
        'contacts': Contact.objects.all(),
    }
    return render(request, 'leads/quotation_form.html', context)


@login_required
def quotation_detail(request, pk):
    quotation = get_object_or_404(Quotation, pk=pk)
    context = {
        'quotation': quotation,
        'items': quotation.items.all(),
        'active': 'quotations',
        'status_choices': QUOTATION_STATUS_CHOICES,
    }
    return render(request, 'leads/quotation_detail.html', context)


@login_required
@block_view_only
def quotation_edit(request, pk):
    quotation = get_object_or_404(Quotation, pk=pk)
    if request.method == 'POST':
        quotation.title = request.POST.get('title')
        quotation.status = request.POST.get('status', 'draft')
        quotation.valid_until = request.POST.get('valid_until') or None
        quotation.notes = request.POST.get('notes')
        quotation.terms = request.POST.get('terms')
        opp_id = request.POST.get('opportunity')
        lead_id = request.POST.get('lead')
        company_id = request.POST.get('company')
        contact_id = request.POST.get('contact')
        quotation.opportunity_id = opp_id if opp_id else None
        quotation.lead_id = lead_id if lead_id else None
        quotation.company_id = company_id if company_id else None
        quotation.contact_id = contact_id if contact_id else None
        quotation.save()

        # replace line items
        quotation.items.all().delete()
        descriptions = request.POST.getlist('description')
        quantities = request.POST.getlist('quantity')
        unit_prices = request.POST.getlist('unit_price')
        for desc, qty, price in zip(descriptions, quantities, unit_prices):
            if desc.strip():
                QuotationItem.objects.create(
                    quotation=quotation,
                    description=desc,
                    quantity=qty or 1,
                    unit_price=price or 0,
                )

        messages.success(request, 'Quotation updated.')
        return redirect('quotation_detail', pk=quotation.pk)

    context = {
        'active': 'quotations',
        'title': 'Edit Quotation',
        'quotation': quotation,
        'items': quotation.items.all(),
        'status_choices': QUOTATION_STATUS_CHOICES,
        'opportunities': Opportunity.objects.all(),
        'leads': Lead.objects.all(),
        'companies': Company.objects.all(),
        'contacts': Contact.objects.all(),
    }
    return render(request, 'leads/quotation_form.html', context)


@login_required
@block_view_only
def quotation_delete(request, pk):
    quotation = get_object_or_404(Quotation, pk=pk)
    quotation.delete()
    messages.success(request, 'Quotation deleted.')
    return redirect('quotation_list')


@login_required
@block_view_only
def quotation_status(request, pk, status):
    quotation = get_object_or_404(Quotation, pk=pk)
    valid = dict(QUOTATION_STATUS_CHOICES)
    if status in valid:
        quotation.status = status
        quotation.save()
        messages.success(request, f'Quotation marked as {valid[status]}.')
    return redirect('quotation_detail', pk=pk)

# ── PROJECT VIEWS ──────────────────────────────────────────

@login_required
def project_list(request):
    projects = Project.objects.select_related('manager', 'company').all()
    status = request.GET.get('status')
    if status:
        projects = projects.filter(status=status)
    q = request.GET.get('q')
    if q:
        projects = projects.filter(Q(name__icontains=q) | Q(company__name__icontains=q))
    context = {
        'projects': projects,
        'active': 'projects',
        'title': 'Projects',
        'status_choices': PROJECT_STATUS_CHOICES,
        'selected_status': status,
    }
    return render(request, 'leads/project_list.html', context)


@login_required
@block_view_only
def project_create(request, opp_pk=None):
    opportunity = None
    if opp_pk:
        opportunity = get_object_or_404(Opportunity, pk=opp_pk)

    if request.method == 'POST':
        project = Project(
            name=request.POST.get('name'),
            description=request.POST.get('description'),
            status=request.POST.get('status', 'planning'),
            priority=request.POST.get('priority', 'medium'),
            methodology=request.POST.get('methodology', 'agile'),
            budget=request.POST.get('budget') or 0,
            start_date=request.POST.get('start_date') or None,
            end_date=request.POST.get('end_date') or None,
            estimated_hours=request.POST.get('estimated_hours') or 0,
            technology_stack=request.POST.get('technology_stack'),
            notes=request.POST.get('notes'),
        )
        manager_id = request.POST.get('manager')
        company_id = request.POST.get('company')
        contact_id = request.POST.get('contact')
        opp_id = request.POST.get('opportunity')
        if manager_id:
            project.manager_id = manager_id
        if company_id:
            project.company_id = company_id
        if contact_id:
            project.contact_id = contact_id
        if opp_id:
            project.opportunity_id = opp_id
        project.save()

        team_ids = request.POST.getlist('team')
        if team_ids:
            project.team.set(team_ids)

        # mark opportunity as won if converting
        if opportunity:
            opportunity.stage = 'won'
            opportunity.save()

        messages.success(request, f'Project "{project.name}" created.')
        return redirect('project_detail', pk=project.pk)

    context = {
        'active': 'projects',
        'title': 'Create Project',
        'opportunity': opportunity,
        'status_choices': PROJECT_STATUS_CHOICES,
        'priority_choices': PROJECT_PRIORITY_CHOICES,
        'methodology_choices': METHODOLOGY_CHOICES,
        'users': User.objects.all(),
        'companies': Company.objects.all(),
        'contacts': Contact.objects.all(),
        'opportunities': Opportunity.objects.filter(stage='won'),
    }
    return render(request, 'leads/project_form.html', context)


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    milestones = project.milestones.prefetch_related('tasks').all()
    context = {
        'project': project,
        'milestones': milestones,
        'active': 'projects',
        'task_status_choices': TASK_STATUS_CHOICES,
        'task_priority_choices': TASK_PRIORITY_CHOICES,
        'milestone_status_choices': MILESTONE_STATUS_CHOICES,
        'users': User.objects.all(),
        'today': timezone.localdate(),
    }
    return render(request, 'leads/project_detail.html', context)


@login_required
@block_view_only
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        project.name = request.POST.get('name')
        project.description = request.POST.get('description')
        project.status = request.POST.get('status', 'planning')
        project.priority = request.POST.get('priority', 'medium')
        project.methodology = request.POST.get('methodology', 'agile')
        project.budget = request.POST.get('budget') or 0
        project.start_date = request.POST.get('start_date') or None
        project.end_date = request.POST.get('end_date') or None
        project.estimated_hours = request.POST.get('estimated_hours') or 0
        project.technology_stack = request.POST.get('technology_stack')
        project.notes = request.POST.get('notes')
        manager_id = request.POST.get('manager')
        company_id = request.POST.get('company')
        contact_id = request.POST.get('contact')
        project.manager_id = manager_id if manager_id else None
        project.company_id = company_id if company_id else None
        project.contact_id = contact_id if contact_id else None
        project.save()
        team_ids = request.POST.getlist('team')
        project.team.set(team_ids)
        messages.success(request, 'Project updated.')
        return redirect('project_detail', pk=pk)

    context = {
        'active': 'projects',
        'title': 'Edit Project',
        'project': project,
        'status_choices': PROJECT_STATUS_CHOICES,
        'priority_choices': PROJECT_PRIORITY_CHOICES,
        'methodology_choices': METHODOLOGY_CHOICES,
        'users': User.objects.all(),
        'companies': Company.objects.all(),
        'contacts': Contact.objects.all(),
        'opportunities': Opportunity.objects.filter(stage='won'),
    }
    return render(request, 'leads/project_form.html', context)


@login_required
@block_view_only
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    project.delete()
    messages.success(request, 'Project deleted.')
    return redirect('project_list')


# ── MILESTONE VIEWS ────────────────────────────────────────

@login_required
@block_view_only
def milestone_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    if request.method == 'POST':
        milestone = Milestone(
            project=project,
            title=request.POST.get('title'),
            description=request.POST.get('description'),
            status=request.POST.get('status', 'pending'),
            start_date=request.POST.get('start_date') or None,
            end_date=request.POST.get('end_date') or None,
            order=project.milestones.count() + 1,
        )
        assigned_id = request.POST.get('assigned_to')
        if assigned_id:
            milestone.assigned_to_id = assigned_id
        milestone.save()
        messages.success(request, 'Milestone added.')
    return redirect('project_detail', pk=project_pk)


@login_required
@block_view_only
def milestone_edit(request, pk):
    milestone = get_object_or_404(Milestone, pk=pk)
    if request.method == 'POST':
        milestone.title = request.POST.get('title')
        milestone.description = request.POST.get('description')
        milestone.status = request.POST.get('status', 'pending')
        milestone.start_date = request.POST.get('start_date') or None
        milestone.end_date = request.POST.get('end_date') or None
        assigned_id = request.POST.get('assigned_to')
        milestone.assigned_to_id = assigned_id if assigned_id else None
        milestone.save()
        messages.success(request, 'Milestone updated.')
    return redirect('project_detail', pk=milestone.project.pk)


@login_required
@block_view_only
def milestone_delete(request, pk):
    milestone = get_object_or_404(Milestone, pk=pk)
    project_pk = milestone.project.pk
    milestone.delete()
    messages.success(request, 'Milestone deleted.')
    return redirect('project_detail', pk=project_pk)


# ── TASK VIEWS ─────────────────────────────────────────────

@login_required
@block_view_only
def task_create(request, milestone_pk):
    milestone = get_object_or_404(Milestone, pk=milestone_pk)
    if request.method == 'POST':
        task = Task(
            milestone=milestone,
            title=request.POST.get('title'),
            description=request.POST.get('description'),
            status=request.POST.get('status', 'todo'),
            priority=request.POST.get('priority', 'medium'),
            due_date=request.POST.get('due_date') or None,
            notes=request.POST.get('notes'),
        )
        assigned_id = request.POST.get('assigned_to')
        if assigned_id:
            task.assigned_to_id = assigned_id
        task.save()
        messages.success(request, 'Task added.')
    return redirect('project_detail', pk=milestone.project.pk)


@login_required
@block_view_only
def task_edit(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if request.method == 'POST':
        task.title = request.POST.get('title')
        task.description = request.POST.get('description')
        task.status = request.POST.get('status', 'todo')
        task.priority = request.POST.get('priority', 'medium')
        task.due_date = request.POST.get('due_date') or None
        task.notes = request.POST.get('notes')
        assigned_id = request.POST.get('assigned_to')
        task.assigned_to_id = assigned_id if assigned_id else None
        task.save()
        messages.success(request, 'Task updated.')
    return redirect('project_detail', pk=task.milestone.project.pk)


@login_required
@block_view_only
@require_POST
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk)
    project_pk = task.milestone.project.pk
    task.delete()
    messages.success(request, 'Task deleted.')
    return redirect('project_detail', pk=project_pk)


@login_required
@block_view_only
def task_status(request, pk, status):
    task = get_object_or_404(Task, pk=pk)
    valid = dict(TASK_STATUS_CHOICES)
    if status in valid:
        task.status = status
        task.save()
    return redirect(request.META.get('HTTP_REFERER', 'project_list'))


@login_required
def convert_to_project(request, opp_pk):
    """One-click convert a won opportunity to a project."""
    opportunity = get_object_or_404(Opportunity, pk=opp_pk)
    if hasattr(opportunity, 'project'):
        messages.info(request, 'This opportunity already has a project.')
        return redirect('project_detail', pk=opportunity.project.pk)
    return redirect('project_create_from_opp', opp_pk=opp_pk)

# ── MEETING VIEWS ──────────────────────────────────────────

@login_required
def meeting_list(request):
    today = timezone.localdate()
    meetings = Meeting.objects.select_related(
        'lead', 'opportunity', 'company', 'created_by'
    ).all()

    scope = request.GET.get('scope', 'all')
    if scope == 'upcoming':
        meetings = meetings.filter(
            scheduled_at__date__gte=today,
            status='scheduled'
        )
    elif scope == 'today':
        meetings = meetings.filter(scheduled_at__date=today)
    elif scope == 'past':
        meetings = meetings.filter(scheduled_at__date__lt=today)

    q = request.GET.get('q')
    if q:
        meetings = meetings.filter(
            Q(title__icontains=q) | Q(company__name__icontains=q)
        )

    context = {
        'meetings': meetings,
        'active': 'meetings',
        'title': 'Meetings',
        'scope': scope,
    }
    return render(request, 'leads/meeting_list.html', context)


@login_required
@block_view_only
def meeting_create(request):
    if request.method == 'POST':
        scheduled_at = request.POST.get('scheduled_at')
        if not scheduled_at:
            messages.error(request, 'Please select a date and time for the meeting.')
            context = {
                'active': 'meetings',
                'title': 'Schedule Meeting',
                'meeting_types': MEETING_TYPE_CHOICES,
                'meeting_statuses': MEETING_STATUS_CHOICES,
                'leads': Lead.objects.all(),
                'opportunities': Opportunity.objects.all(),
                'companies': Company.objects.all(),
                'contacts': Contact.objects.all(),
                'users': User.objects.all(),
            }
            return render(request, 'leads/meeting_form.html', context)

        meeting = Meeting(
            title=request.POST.get('title'),
            meeting_type=request.POST.get('meeting_type', 'call'),
            status=request.POST.get('status', 'scheduled'),
            scheduled_at=scheduled_at,
            duration_minutes=request.POST.get('duration_minutes') or 30,
            location=request.POST.get('location'),
            agenda=request.POST.get('agenda'),
            notes=request.POST.get('notes'),
            action_items=request.POST.get('action_items'),
            created_by=request.user,
        )
        lead_id = request.POST.get('lead')
        opp_id = request.POST.get('opportunity')
        company_id = request.POST.get('company')
        contact_id = request.POST.get('contact')
        meeting.lead_id = lead_id if lead_id else None
        meeting.opportunity_id = opp_id if opp_id else None
        meeting.company_id = company_id if company_id else None
        meeting.contact_id = contact_id if contact_id else None
        meeting.save()
        attendee_ids = request.POST.getlist('attendees')
        if attendee_ids:
            meeting.attendees.set(attendee_ids)
        messages.success(request, 'Meeting scheduled.')
        return redirect('meeting_detail', pk=meeting.pk)

    context = {
        'active': 'meetings',
        'title': 'Schedule Meeting',
        'meeting_types': MEETING_TYPE_CHOICES,
        'meeting_statuses': MEETING_STATUS_CHOICES,
        'leads': Lead.objects.all(),
        'opportunities': Opportunity.objects.all(),
        'companies': Company.objects.all(),
        'contacts': Contact.objects.all(),
        'users': User.objects.all(),
    }
    return render(request, 'leads/meeting_form.html', context)

@login_required
def meeting_detail(request, pk):
    meeting = get_object_or_404(Meeting, pk=pk)
    context = {
        'meeting': meeting,
        'active': 'meetings',
        'meeting_statuses': MEETING_STATUS_CHOICES,
    }
    return render(request, 'leads/meeting_detail.html', context)


@login_required
@block_view_only
def meeting_edit(request, pk):
    meeting = get_object_or_404(Meeting, pk=pk)
    if request.method == 'POST':
        meeting.title = request.POST.get('title')
        meeting.meeting_type = request.POST.get('meeting_type', 'call')
        meeting.status = request.POST.get('status', 'scheduled')
        meeting.scheduled_at = request.POST.get('scheduled_at')
        meeting.duration_minutes = request.POST.get('duration_minutes') or 30
        meeting.location = request.POST.get('location')
        meeting.agenda = request.POST.get('agenda')
        meeting.notes = request.POST.get('notes')
        meeting.action_items = request.POST.get('action_items')
        lead_id = request.POST.get('lead')
        opp_id = request.POST.get('opportunity')
        company_id = request.POST.get('company')
        contact_id = request.POST.get('contact')
        meeting.lead_id = lead_id if lead_id else None
        meeting.opportunity_id = opp_id if opp_id else None
        meeting.company_id = company_id if company_id else None
        meeting.contact_id = contact_id if contact_id else None
        meeting.save()
        attendee_ids = request.POST.getlist('attendees')
        meeting.attendees.set(attendee_ids)
        messages.success(request, 'Meeting updated.')
        return redirect('meeting_detail', pk=pk)

    context = {
        'active': 'meetings',
        'title': 'Edit Meeting',
        'meeting': meeting,
        'meeting_types': MEETING_TYPE_CHOICES,
        'meeting_statuses': MEETING_STATUS_CHOICES,
        'leads': Lead.objects.all(),
        'opportunities': Opportunity.objects.all(),
        'companies': Company.objects.all(),
        'contacts': Contact.objects.all(),
        'users': User.objects.all(),
    }
    return render(request, 'leads/meeting_form.html', context)


@login_required
@block_view_only
def meeting_delete(request, pk):
    meeting = get_object_or_404(Meeting, pk=pk)
    meeting.delete()
    messages.success(request, 'Meeting deleted.')
    return redirect('meeting_list')


@login_required
@block_view_only
def meeting_status(request, pk, status):
    meeting = get_object_or_404(Meeting, pk=pk)
    valid = dict(MEETING_STATUS_CHOICES)
    if status in valid:
        meeting.status = status
        meeting.save()
        messages.success(request, f'Meeting marked as {valid[status]}.')
    return redirect('meeting_detail', pk=pk)


# ── GENERAL TASK VIEWS ─────────────────────────────────────

@login_required
def general_task_list(request):
    today = timezone.localdate()
    tasks = GeneralTask.objects.select_related('assigned_to', 'created_by').all()

    scope = request.GET.get('scope', 'all')
    if scope == 'mine':
        tasks = tasks.filter(assigned_to=request.user)
    elif scope == 'today':
        tasks = tasks.filter(due_date=today)
    elif scope == 'overdue':
        tasks = tasks.filter(due_date__lt=today, status__in=['todo', 'in_progress'])

    status = request.GET.get('status')
    if status:
        tasks = tasks.filter(status=status)

    context = {
        'tasks': tasks,
        'active': 'general_tasks',
        'title': 'Tasks',
        'scope': scope,
        'status_choices': GENERAL_TASK_STATUS_CHOICES,
        'priority_choices': GENERAL_TASK_PRIORITY_CHOICES,
        'selected_status': status,
    }
    return render(request, 'leads/general_task_list.html', context)


@login_required
@block_view_only
def general_task_create(request):
    if request.method == 'POST':
        task = GeneralTask(
            title=request.POST.get('title'),
            description=request.POST.get('description'),
            status=request.POST.get('status', 'todo'),
            priority=request.POST.get('priority', 'medium'),
            due_date=request.POST.get('due_date') or None,
            created_by=request.user,
        )
        assigned_id = request.POST.get('assigned_to')
        lead_id = request.POST.get('lead')
        opp_id = request.POST.get('opportunity')
        task.assigned_to_id = assigned_id if assigned_id else None
        task.lead_id = lead_id if lead_id else None
        task.opportunity_id = opp_id if opp_id else None
        task.save()
        messages.success(request, 'Task created.')
        return redirect('general_task_list')

    context = {
        'active': 'general_tasks',
        'title': 'Create Task',
        'status_choices': GENERAL_TASK_STATUS_CHOICES,
        'priority_choices': GENERAL_TASK_PRIORITY_CHOICES,
        'users': User.objects.all(),
        'leads': Lead.objects.all(),
        'opportunities': Opportunity.objects.all(),
    }
    return render(request, 'leads/general_task_form.html', context)


@login_required
@block_view_only
def general_task_edit(request, pk):
    task = get_object_or_404(GeneralTask, pk=pk)
    if request.method == 'POST':
        task.title = request.POST.get('title')
        task.description = request.POST.get('description')
        task.status = request.POST.get('status', 'todo')
        task.priority = request.POST.get('priority', 'medium')
        task.due_date = request.POST.get('due_date') or None
        assigned_id = request.POST.get('assigned_to')
        lead_id = request.POST.get('lead')
        opp_id = request.POST.get('opportunity')
        task.assigned_to_id = assigned_id if assigned_id else None
        task.lead_id = lead_id if lead_id else None
        task.opportunity_id = opp_id if opp_id else None
        task.save()
        messages.success(request, 'Task updated.')
        return redirect('general_task_list')

    context = {
        'active': 'general_tasks',
        'title': 'Edit Task',
        'task': task,
        'status_choices': GENERAL_TASK_STATUS_CHOICES,
        'priority_choices': GENERAL_TASK_PRIORITY_CHOICES,
        'users': User.objects.all(),
        'leads': Lead.objects.all(),
        'opportunities': Opportunity.objects.all(),
    }
    return render(request, 'leads/general_task_form.html', context)


@login_required
@block_view_only
def general_task_delete(request, pk):
    task = get_object_or_404(GeneralTask, pk=pk)
    task.delete()
    messages.success(request, 'Task deleted.')
    return redirect('general_task_list')


@login_required
@block_view_only
def general_task_status(request, pk, status):
    task = get_object_or_404(GeneralTask, pk=pk)
    valid = dict(GENERAL_TASK_STATUS_CHOICES)
    if status in valid:
        task.status = status
        task.save()
    return redirect(request.META.get('HTTP_REFERER', 'general_task_list'))

# ── COMMUNICATION LOG VIEWS ────────────────────────────────

@login_required
def communication_list(request):
    logs = CommunicationLog.objects.select_related(
        'created_by', 'lead', 'contact', 'company', 'opportunity', 'project'
    ).all()

    comm_type = request.GET.get('type')
    if comm_type:
        logs = logs.filter(comm_type=comm_type)

    q = request.GET.get('q')
    if q:
        logs = logs.filter(
            Q(subject__icontains=q) | Q(body__icontains=q)
        )

    context = {
        'logs': logs,
        'active': 'communications',
        'title': 'Communication Log',
        'comm_types': COMMUNICATION_TYPE_CHOICES,
        'selected_type': comm_type,
    }
    return render(request, 'leads/communication_list.html', context)


@login_required
@block_view_only
def communication_create(request):
    if request.method == 'POST':
        log = CommunicationLog(
            comm_type=request.POST.get('comm_type', 'note'),
            direction=request.POST.get('direction', 'outbound'),
            subject=request.POST.get('subject'),
            body=request.POST.get('body'),
            created_by=request.user,
        )
        lead_id = request.POST.get('lead')
        opp_id = request.POST.get('opportunity')
        contact_id = request.POST.get('contact')
        company_id = request.POST.get('company')
        project_id = request.POST.get('project')
        log.lead_id = lead_id if lead_id else None
        log.opportunity_id = opp_id if opp_id else None
        log.contact_id = contact_id if contact_id else None
        log.company_id = company_id if company_id else None
        log.project_id = project_id if project_id else None
        log.save()
        messages.success(request, 'Communication logged.')

        # redirect back to wherever they came from
        next_url = request.POST.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('communication_list')

    context = {
        'active': 'communications',
        'title': 'Log Communication',
        'comm_types': COMMUNICATION_TYPE_CHOICES,
        'directions': COMMUNICATION_DIRECTION_CHOICES,
        'leads': Lead.objects.all(),
        'opportunities': Opportunity.objects.all(),
        'contacts': Contact.objects.all(),
        'companies': Company.objects.all(),
        'projects': Project.objects.all(),
        # pre-fill from query params if coming from a detail page
        'preselect_lead': request.GET.get('lead'),
        'preselect_contact': request.GET.get('contact'),
        'preselect_company': request.GET.get('company'),
        'preselect_opportunity': request.GET.get('opportunity'),
        'preselect_project': request.GET.get('project'),
    }
    return render(request, 'leads/communication_form.html', context)


@login_required
@block_view_only
def communication_delete(request, pk):
    log = get_object_or_404(CommunicationLog, pk=pk)
    log.delete()
    messages.success(request, 'Log deleted.')
    return redirect(request.META.get('HTTP_REFERER', 'communication_list'))


@login_required
def communication_timeline(request):
    """
    Unified timeline — filter by lead, contact, company or opportunity.
    Used as an embedded view from detail pages.
    """
    logs = CommunicationLog.objects.select_related(
        'created_by', 'lead', 'contact', 'company'
    ).all()

    lead_id = request.GET.get('lead')
    contact_id = request.GET.get('contact')
    company_id = request.GET.get('company')
    opp_id = request.GET.get('opportunity')
    project_id = request.GET.get('project')

    if lead_id:
        logs = logs.filter(lead_id=lead_id)
    if contact_id:
        logs = logs.filter(contact_id=contact_id)
    if company_id:
        logs = logs.filter(company_id=company_id)
    if opp_id:
        logs = logs.filter(opportunity_id=opp_id)
    if project_id:
        logs = logs.filter(project_id=project_id)

    context = {
        'logs': logs,
        'active': 'communications',
        'title': 'Communication Timeline',
        'comm_types': COMMUNICATION_TYPE_CHOICES,
    }
    return render(request, 'leads/communication_timeline.html', context)

# ── REPORTS & ANALYTICS ────────────────────────────────────

@login_required
def reports(request):
    today = timezone.localdate()
    this_month = today.replace(day=1)

    # ── Lead Stats ──────────────────────────────────────────
    leads = Lead.objects.all()
    total_leads = leads.count()
    leads_this_month = leads.filter(created_at__date__gte=this_month).count()

    leads_by_status = {}
    for status, label in Lead._meta.get_field('status').choices:
        leads_by_status[label] = leads.filter(status=status).count()

    leads_by_source = {}
    for source, label in Lead._meta.get_field('lead_source').choices:
        count = leads.filter(lead_source=source).count()
        if count > 0:
            leads_by_source[label] = count

    # ── Pipeline Stats ──────────────────────────────────────
    opportunities = Opportunity.objects.all()
    total_pipeline_value = opportunities.exclude(
        stage__in=['lost']
    ).aggregate(total=Sum('value'))['total'] or 0

    won_value = opportunities.filter(
        stage='won'
    ).aggregate(total=Sum('value'))['total'] or 0

    total_opps = opportunities.count()
    won_opps = opportunities.filter(stage='won').count()
    win_rate = int((won_opps / total_opps) * 100) if total_opps > 0 else 0

    pipeline_by_stage = {}
    for stage, label in OPPORTUNITY_STAGE_CHOICES:
        pipeline_by_stage[label] = {
            'count': opportunities.filter(stage=stage).count(),
            'value': opportunities.filter(stage=stage).aggregate(
                total=Sum('value')
            )['total'] or 0,
        }

    # ── SPO Performance ─────────────────────────────────────
    spo_stats = []
    for spo in SalesPerson.objects.all():
        spo_leads = leads.filter(spo=spo)
        spo_stats.append({
            'name': spo.name,
            'total': spo_leads.count(),
            'new': spo_leads.filter(status='new').count(),
            'positive': spo_leads.filter(status='positive').count(),
            'converted': spo_leads.filter(status='converted').count(),
            'lost': spo_leads.filter(status='lost').count(),
            'conversion_rate': int(
                (spo_leads.filter(status='converted').count() /
                 spo_leads.count()) * 100
            ) if spo_leads.count() > 0 else 0,
        })

    # ── Payment Stats ───────────────────────────────────────
    payments = Payment.objects.all()
    total_revenue = payments.aggregate(total=Sum('amount'))['total'] or 0
    advance_revenue = payments.filter(
        payment_type='advance'
    ).aggregate(total=Sum('amount'))['total'] or 0
    full_revenue = payments.filter(
        payment_type='full'
    ).aggregate(total=Sum('amount'))['total'] or 0

    # ── Project Stats ───────────────────────────────────────
    projects = Project.objects.all()
    project_by_status = {}
    for status, label in PROJECT_STATUS_CHOICES:
        project_by_status[label] = projects.filter(status=status).count()

    # ── Meeting Stats ───────────────────────────────────────
    meetings = Meeting.objects.all()
    meeting_by_type = {}
    for mtype, label in MEETING_TYPE_CHOICES:
        count = meetings.filter(meeting_type=mtype).count()
        if count > 0:
            meeting_by_type[label] = count

    # ── Followup Stats ───────────────────────────────────────
    followups = FollowUp.objects.all()
    followup_done = followups.filter(status='done').count()
    followup_pending = followups.filter(status='pending').count()

    context = {
        'active': 'reports',
        'title': 'Reports & Analytics',

        # leads
        'total_leads': total_leads,
        'leads_this_month': leads_this_month,
        'leads_by_status': leads_by_status,
        'leads_by_source': leads_by_source,

        # pipeline
        'total_pipeline_value': total_pipeline_value,
        'won_value': won_value,
        'win_rate': win_rate,
        'total_opps': total_opps,
        'won_opps': won_opps,
        'pipeline_by_stage': pipeline_by_stage,

        # spo
        'spo_stats': spo_stats,

        # payments
        'total_revenue': total_revenue,
        'advance_revenue': advance_revenue,
        'full_revenue': full_revenue,

        # projects
        'project_by_status': project_by_status,

        # meetings
        'meeting_by_type': meeting_by_type,

        # followups
        'followup_done': followup_done,
        'followup_pending': followup_pending,
    }
    return render(request, 'leads/reports.html', context)

# ── SUPPORT TICKET VIEWS ───────────────────────────────────

@login_required
def ticket_list(request):
    tickets = Ticket.objects.select_related(
        'created_by', 'assigned_to', 'company'
    ).all()

    status = request.GET.get('status')
    if status:
        tickets = tickets.filter(status=status)

    priority = request.GET.get('priority')
    if priority:
        tickets = tickets.filter(priority=priority)

    q = request.GET.get('q')
    if q:
        tickets = tickets.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        )

    context = {
        'tickets': tickets,
        'active': 'tickets',
        'title': 'Support Tickets',
        'status_choices': TICKET_STATUS_CHOICES,
        'priority_choices': TICKET_PRIORITY_CHOICES,
        'selected_status': status,
        'selected_priority': priority,
    }
    return render(request, 'leads/ticket_list.html', context)


@login_required
@block_view_only
def ticket_create(request):
    if request.method == 'POST':
        ticket = Ticket(
            title=request.POST.get('title'),
            description=request.POST.get('description'),
            status=request.POST.get('status', 'open'),
            priority=request.POST.get('priority', 'medium'),
            category=request.POST.get('category', 'support'),
            created_by=request.user,
        )
        assigned_id = request.POST.get('assigned_to')
        lead_id = request.POST.get('lead')
        company_id = request.POST.get('company')
        contact_id = request.POST.get('contact')
        project_id = request.POST.get('project')
        ticket.assigned_to_id = assigned_id if assigned_id else None
        ticket.lead_id = lead_id if lead_id else None
        ticket.company_id = company_id if company_id else None
        ticket.contact_id = contact_id if contact_id else None
        ticket.project_id = project_id if project_id else None
        ticket.save()
        if ticket.assigned_to:
            create_notification(
                user=ticket.assigned_to,
                notif_type='ticket_assigned',
                title=f'New ticket assigned: #{ticket.pk}',
                message=f'You have been assigned ticket "{ticket.title}".',
                link=f'/tickets/{ticket.pk}/',
            )
        messages.success(request, f'Ticket #{ticket.pk} created.')
        return redirect('ticket_detail', pk=ticket.pk)

    context = {
        'active': 'tickets',
        'title': 'Create Ticket',
        'status_choices': TICKET_STATUS_CHOICES,
        'priority_choices': TICKET_PRIORITY_CHOICES,
        'category_choices': TICKET_CATEGORY_CHOICES,
        'users': User.objects.all(),
        'leads': Lead.objects.all(),
        'companies': Company.objects.all(),
        'contacts': Contact.objects.all(),
        'projects': Project.objects.all(),
    }
    return render(request, 'leads/ticket_form.html', context)


@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)

    if request.method == 'POST':
        body = request.POST.get('body')
        if body:
            TicketReply.objects.create(
                ticket=ticket,
                author=request.user,
                body=body,
            )
            # update status if replying
            new_status = request.POST.get('status')
            if new_status:
                ticket.status = new_status
                if new_status == 'resolved':
                    ticket.resolved_at = timezone.now()
                ticket.save()
            messages.success(request, 'Reply added.')
            return redirect('ticket_detail', pk=pk)

    context = {
        'ticket': ticket,
        'replies': ticket.replies.all(),
        'active': 'tickets',
        'status_choices': TICKET_STATUS_CHOICES,
    }
    return render(request, 'leads/ticket_detail.html', context)


@login_required
@block_view_only
def ticket_edit(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.method == 'POST':
        ticket.title = request.POST.get('title')
        ticket.description = request.POST.get('description')
        ticket.status = request.POST.get('status', 'open')
        ticket.priority = request.POST.get('priority', 'medium')
        ticket.category = request.POST.get('category', 'support')
        assigned_id = request.POST.get('assigned_to')
        lead_id = request.POST.get('lead')
        company_id = request.POST.get('company')
        contact_id = request.POST.get('contact')
        project_id = request.POST.get('project')
        ticket.assigned_to_id = assigned_id if assigned_id else None
        ticket.lead_id = lead_id if lead_id else None
        ticket.company_id = company_id if company_id else None
        ticket.contact_id = contact_id if contact_id else None
        ticket.project_id = project_id if project_id else None
        if ticket.status == 'resolved' and not ticket.resolved_at:
            ticket.resolved_at = timezone.now()
        ticket.save()
        messages.success(request, 'Ticket updated.')
        return redirect('ticket_detail', pk=pk)

    context = {
        'active': 'tickets',
        'title': 'Edit Ticket',
        'ticket': ticket,
        'status_choices': TICKET_STATUS_CHOICES,
        'priority_choices': TICKET_PRIORITY_CHOICES,
        'category_choices': TICKET_CATEGORY_CHOICES,
        'users': User.objects.all(),
        'leads': Lead.objects.all(),
        'companies': Company.objects.all(),
        'contacts': Contact.objects.all(),
        'projects': Project.objects.all(),
    }
    return render(request, 'leads/ticket_form.html', context)


@login_required
@block_view_only
def ticket_delete(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    ticket.delete()
    messages.success(request, 'Ticket deleted.')
    return redirect('ticket_list')


@login_required
@block_view_only
def ticket_status(request, pk, status):
    ticket = get_object_or_404(Ticket, pk=pk)
    valid = dict(TICKET_STATUS_CHOICES)
    if status in valid:
        ticket.status = status
        if status == 'resolved':
            ticket.resolved_at = timezone.now()
        ticket.save()
        messages.success(request, f'Ticket marked as {valid[status]}.')
    return redirect('ticket_detail', pk=pk)

# ── ACTIVITY LOG VIEW ──────────────────────────────────────

@login_required
def activity_log(request):
    logs = ActivityLog.objects.select_related('user').all()

    entity_type = request.GET.get('entity')
    if entity_type:
        logs = logs.filter(entity_type=entity_type)

    action = request.GET.get('action')
    if action:
        logs = logs.filter(action=action)

    # only show last 500 to keep it fast
    logs = logs[:500]

    entity_types = ActivityLog.objects.values_list(
        'entity_type', flat=True
    ).distinct().order_by('entity_type')

    context = {
        'logs': logs,
        'active': 'activity_log',
        'title': 'Activity Log',
        'entity_types': entity_types,
        'action_choices': ActivityLog.ACTION_CHOICES,
        'selected_entity': entity_type,
        'selected_action': action,
    }
    return render(request, 'leads/activity_log.html', context)

# ── DOCUMENT VIEWS ─────────────────────────────────────────

@login_required
@block_view_only
def document_upload(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        doc_type = request.POST.get('doc_type', 'other')
        notes = request.POST.get('notes')
        file = request.FILES.get('file')

        if not file:
            messages.error(request, 'Please select a file to upload.')
            return redirect(request.META.get('HTTP_REFERER', 'document_list'))

        doc = Document(
            title=title or file.name,
            doc_type=doc_type,
            notes=notes,
            uploaded_by=request.user,
            file=file,
        )
        lead_id = request.POST.get('lead')
        opp_id = request.POST.get('opportunity')
        project_id = request.POST.get('project')
        ticket_id = request.POST.get('ticket')
        quotation_id = request.POST.get('quotation')
        doc.lead_id = lead_id if lead_id else None
        doc.opportunity_id = opp_id if opp_id else None
        doc.project_id = project_id if project_id else None
        doc.ticket_id = ticket_id if ticket_id else None
        doc.quotation_id = quotation_id if quotation_id else None
        doc.save()
        messages.success(request, f'"{doc.title}" uploaded successfully.')

        next_url = request.POST.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('document_list')

    context = {
        'active': 'documents',
        'title': 'Upload Document',
        'doc_types': DOCUMENT_TYPE_CHOICES,
        'leads': Lead.objects.all(),
        'opportunities': Opportunity.objects.all(),
        'projects': Project.objects.all(),
        'tickets': Ticket.objects.all(),
        'quotations': Quotation.objects.all(),
        'preselect_lead': request.GET.get('lead'),
        'preselect_opportunity': request.GET.get('opportunity'),
        'preselect_project': request.GET.get('project'),
        'preselect_ticket': request.GET.get('ticket'),
        'preselect_quotation': request.GET.get('quotation'),
    }
    return render(request, 'leads/document_upload.html', context)


@login_required
def document_list(request):
    documents = Document.objects.select_related(
        'uploaded_by', 'lead', 'project', 'opportunity'
    ).all()

    doc_type = request.GET.get('type')
    if doc_type:
        documents = documents.filter(doc_type=doc_type)

    q = request.GET.get('q')
    if q:
        documents = documents.filter(Q(title__icontains=q))

    context = {
        'documents': documents,
        'active': 'documents',
        'title': 'Documents',
        'doc_types': DOCUMENT_TYPE_CHOICES,
        'selected_type': doc_type,
    }
    return render(request, 'leads/document_list.html', context)


@login_required
@block_view_only
def document_delete(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    doc.file.delete()
    doc.delete()
    messages.success(request, 'Document deleted.')
    return redirect(request.META.get('HTTP_REFERER', 'document_list'))

# ── CONTRACT VIEWS ─────────────────────────────────────────

@login_required
def contract_list(request):
    contracts = Contract.objects.select_related(
        'company', 'opportunity', 'created_by'
    ).all()

    status = request.GET.get('status')
    if status:
        contracts = contracts.filter(status=status)

    q = request.GET.get('q')
    if q:
        contracts = contracts.filter(Q(title__icontains=q))

    context = {
        'contracts': contracts,
        'active': 'contracts',
        'title': 'Contracts',
        'status_choices': CONTRACT_STATUS_CHOICES,
        'selected_status': status,
    }
    return render(request, 'leads/contract_list.html', context)


@login_required
@block_view_only
def contract_create(request):
    if request.method == 'POST':
        contract = Contract(
            title=request.POST.get('title'),
            status=request.POST.get('status', 'draft'),
            value=request.POST.get('value') or 0,
            start_date=request.POST.get('start_date') or None,
            end_date=request.POST.get('end_date') or None,
            signed_date=request.POST.get('signed_date') or None,
            terms=request.POST.get('terms'),
            notes=request.POST.get('notes'),
            created_by=request.user,
        )
        opp_id = request.POST.get('opportunity')
        quot_id = request.POST.get('quotation')
        company_id = request.POST.get('company')
        contact_id = request.POST.get('contact')
        contract.opportunity_id = opp_id if opp_id else None
        contract.quotation_id = quot_id if quot_id else None
        contract.company_id = company_id if company_id else None
        contract.contact_id = contact_id if contact_id else None

        if request.FILES.get('signed_file'):
            contract.signed_file = request.FILES['signed_file']

        contract.save()
        messages.success(request, f'Contract "{contract.title}" created.')
        return redirect('contract_detail', pk=contract.pk)

    context = {
        'active': 'contracts',
        'title': 'Create Contract',
        'status_choices': CONTRACT_STATUS_CHOICES,
        'opportunities': Opportunity.objects.filter(stage='won'),
        'quotations': Quotation.objects.all(),
        'companies': Company.objects.all(),
        'contacts': Contact.objects.all(),
    }
    return render(request, 'leads/contract_form.html', context)


@login_required
def contract_detail(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    context = {
        'contract': contract,
        'active': 'contracts',
        'status_choices': CONTRACT_STATUS_CHOICES,
    }
    return render(request, 'leads/contract_detail.html', context)


@login_required
@block_view_only
def contract_edit(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    if request.method == 'POST':
        contract.title = request.POST.get('title')
        contract.status = request.POST.get('status', 'draft')
        contract.value = request.POST.get('value') or 0
        contract.start_date = request.POST.get('start_date') or None
        contract.end_date = request.POST.get('end_date') or None
        contract.signed_date = request.POST.get('signed_date') or None
        contract.terms = request.POST.get('terms')
        contract.notes = request.POST.get('notes')
        opp_id = request.POST.get('opportunity')
        quot_id = request.POST.get('quotation')
        company_id = request.POST.get('company')
        contact_id = request.POST.get('contact')
        contract.opportunity_id = opp_id if opp_id else None
        contract.quotation_id = quot_id if quot_id else None
        contract.company_id = company_id if company_id else None
        contract.contact_id = contact_id if contact_id else None
        if request.FILES.get('signed_file'):
            contract.signed_file = request.FILES['signed_file']
        contract.save()
        messages.success(request, 'Contract updated.')
        return redirect('contract_detail', pk=pk)

    context = {
        'active': 'contracts',
        'title': 'Edit Contract',
        'contract': contract,
        'status_choices': CONTRACT_STATUS_CHOICES,
        'opportunities': Opportunity.objects.filter(stage='won'),
        'quotations': Quotation.objects.all(),
        'companies': Company.objects.all(),
        'contacts': Contact.objects.all(),
    }
    return render(request, 'leads/contract_form.html', context)


@login_required
@block_view_only
def contract_delete(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    contract.delete()
    messages.success(request, 'Contract deleted.')
    return redirect('contract_list')


@login_required
@block_view_only
def contract_status(request, pk, status):
    contract = get_object_or_404(Contract, pk=pk)
    valid = dict(CONTRACT_STATUS_CHOICES)
    if status in valid:
        contract.status = status
        if status == 'signed':
            contract.signed_date = timezone.localdate()
        contract.save()
        if status == 'signed':
            for admin_user in User.objects.filter(profile__role__in=['admin', 'ceo']):
                create_notification(
                    user=admin_user,
                    notif_type='contract_signed',
                    title=f'Contract signed: {contract.title}',
                    message=f'Contract "{contract.title}" has been signed.',
                    link=f'/contracts/{contract.pk}/',
                )
        messages.success(request, f'Contract marked as {valid[status]}.')
    return redirect('contract_detail', pk=pk)


# ── NOTIFICATION VIEWS ─────────────────────────────────────

@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user)
    context = {
        'notifications': notifications,
        'active': 'notifications',
        'title': 'Notifications'
    }
    return render(request, 'leads/notification_list.html', context)


@login_required
def notification_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.is_read = True
    notif.save()
    if notif.link:
        return redirect(notif.link)
    return redirect('notification_list')


@login_required
def notification_read_all(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, 'All notifications marked as read.')
    return redirect('notification_list')


@login_required
def notification_delete(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.delete()
    return redirect('notification_list')


@login_required
def score_lead_view(request, pk):
    """Manually trigger AI scoring for a lead."""
    lead = get_object_or_404(Lead, pk=pk)
    success = update_lead_score(lead)
    if success:
        messages.success(
            request,
            f'Lead scored: {lead.ai_score}/100 — {lead.ai_score_reason}'
        )
    else:
        messages.error(request, 'Scoring failed. Check Groq API key.')
    return redirect('lead_detail', pk=pk)


@login_required
def score_all_leads(request):
    """Score all leads in bulk — admin only."""
    leads = Lead.objects.all()
    count = 0
    for lead in leads:
        if update_lead_score(lead):
            count += 1
    messages.success(request, f'{count} leads scored successfully.')
    return redirect('all_leads')


@login_required
def salesperson_list(request):
    salespersons = SalesPerson.objects.select_related('user').all()

    spo_data = []
    for spo in salespersons:
        total = spo.leads.count()
        converted = spo.leads.filter(status='converted').count()
        rate = round((converted / total * 100), 1) if total > 0 else 0
        spo_data.append({
            'spo': spo,
            'total': total,
            'converted': converted,
            'rate': rate,
        })

    context = {
        'spo_data': spo_data,
        'active': 'salespersons',
        'title': 'Sales Persons',
    }
    return render(request, 'leads/salesperson_list.html', context)


@login_required
def salesperson_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        user_id = request.POST.get('user')
        if not name:
            messages.error(request, 'Name is required.')
            return redirect('salesperson_create')
        spo = SalesPerson(name=name)
        if user_id:
            spo.user_id = user_id
        spo.save()
        messages.success(request, f'Sales Person "{name}" created.')
        return redirect('salesperson_list')

    users = User.objects.all()
    return render(request, 'leads/salesperson_form.html', {
        'active': 'salespersons',
        'title': 'Add Sales Person',
        'users': users,
    })


@login_required
def salesperson_edit(request, pk):
    spo = get_object_or_404(SalesPerson, pk=pk)
    if request.method == 'POST':
        spo.name = request.POST.get('name')
        user_id = request.POST.get('user')
        spo.user_id = user_id if user_id else None
        spo.save()
        messages.success(request, 'Sales Person updated.')
        return redirect('salesperson_list')

    users = User.objects.all()
    return render(request, 'leads/salesperson_form.html', {
        'active': 'salespersons',
        'title': 'Edit Sales Person',
        'spo': spo,
        'users': users,
    })


@login_required
def salesperson_delete(request, pk):
    spo = get_object_or_404(SalesPerson, pk=pk)
    spo.delete()
    messages.success(request, 'Sales Person deleted.')
    return redirect('salesperson_list')


@login_required
def closing_probability_view(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    success = update_closing_probability(lead)
    if success:
        messages.success(
            request,
            f'Closing probability: {lead.closing_probability}% — {lead.closing_probability_reason}'
        )
    else:
        messages.error(request, 'Prediction failed.')
    return redirect('lead_detail', pk=pk)


@login_required
def ai_followup_message_view(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    channel = request.GET.get('channel', 'whatsapp')
    message = generate_followup_message(lead, channel=channel)
    context = {
        'lead': lead,
        'message': message,
        'channel': channel,
        'active': 'all_leads',
    }
    return render(request, 'leads/ai_followup_message.html', context)


@login_required
def ai_meeting_summary_view(request, pk):
    meeting = get_object_or_404(Meeting, pk=pk)
    success = save_meeting_summary(meeting)
    if success:
        messages.success(request, 'Meeting summary generated.')
    else:
        messages.error(request, 'Summary generation failed.')
    return redirect('meeting_detail', pk=pk)


@login_required
def sales_forecast_view(request):
    forecast = generate_sales_forecast()
    context = {
        'forecast': forecast,
        'active': 'reports',
        'title': 'AI Sales Forecast',
    }
    return render(request, 'leads/sales_forecast.html', context)


@login_required
def churn_risk_view(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    success = update_churn_risk(lead)
    if success:
        messages.success(
            request,
            f'Churn risk: {lead.churn_risk} — {lead.churn_risk_reason}'
        )
    else:
        messages.error(request, 'Churn prediction failed.')
    return redirect('lead_detail', pk=pk)


@login_required
def churn_risk_all_view(request):
    """Shows all leads with high churn risk."""
    high_risk = get_high_churn_leads(limit=50)
    context = {
        'leads': high_risk,
        'active': 'churn',
        'title': 'High Churn Risk Leads',
    }
    return render(request, 'leads/churn_risk_list.html', context)


@login_required
def upsell_recommendations_view(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    recommendations = get_upsell_recommendations(lead)
    context = {
        'lead': lead,
        'recommendations': recommendations,
        'active': 'all_leads',
        'title': f'Upsell Opportunities — {lead.name}',
    }
    return render(request, 'leads/upsell_recommendations.html', context)


@login_required
def lifetime_value_view(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    success = update_lifetime_value(lead)
    if success:
        messages.success(
            request,
            f'Lifetime value estimated: {lead.lifetime_value}'
        )
    else:
        messages.error(request, 'LTV estimation failed.')
    return redirect('lead_detail', pk=pk)


@login_required
def customer_360_view(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    context = {
        'lead': lead,
        'followups': lead.followups.all(),
        'payments': lead.payments.all(),
        'communications': lead.communications.all(),
        'meetings': lead.meetings.all(),
        'tickets': lead.tickets.all(),
        'documents': lead.documents.all(),
        'quotations': lead.quotations.all(),
        'scheduled_payments': lead.scheduled_payments.all(),
        'active': 'all_leads',
        'title': f'360° View — {lead.name}',
    }
    return render(request, 'leads/customer_360.html', context)


@login_required
def ceo_dashboard(request):
    from django.db.models import Sum, Count
    from django.utils import timezone

    today = timezone.localdate()
    this_month = today.replace(day=1)

    # ── Revenue ────────────────────────────────────────────
    total_revenue = Payment.objects.aggregate(
        total=Sum('amount')
    )['total'] or 0

    this_month_revenue = Payment.objects.filter(
        date__date__gte=this_month
    ).aggregate(total=Sum('amount'))['total'] or 0

    advance_revenue = Payment.objects.filter(
        payment_type='advance'
    ).aggregate(total=Sum('amount'))['total'] or 0

    full_revenue = Payment.objects.filter(
        payment_type='full'
    ).aggregate(total=Sum('amount'))['total'] or 0

    # ── Pipeline ───────────────────────────────────────────
    leads = Lead.objects.all()
    total_leads = leads.count()
    new_leads = leads.filter(status='new').count()
    positive_leads = leads.filter(status='positive').count()
    converted_leads = leads.filter(status='converted').count()
    lost_leads = leads.filter(status='lost').count()
    quotation_leads = leads.filter(status='quotation').count()

    conversion_rate = round(
        (converted_leads / total_leads * 100)
        if total_leads > 0 else 0, 1
    )

    pipeline_value = leads.filter(
        status__in=['positive', 'quotation']
    ).aggregate(total=Sum('quotation'))['total'] or 0

    # ── Team Performance ───────────────────────────────────
    spo_performance = []
    for spo in SalesPerson.objects.all():
        spo_leads = leads.filter(spo=spo)
        spo_total = spo_leads.count()
        spo_converted = spo_leads.filter(status='converted').count()
        spo_rate = round(
            (spo_converted / spo_total * 100)
            if spo_total > 0 else 0, 1
        )
        spo_revenue = Payment.objects.filter(
            lead__spo=spo
        ).aggregate(total=Sum('amount'))['total'] or 0

        spo_performance.append({
            'name': spo.name,
            'total': spo_total,
            'converted': spo_converted,
            'rate': spo_rate,
            'revenue': spo_revenue,
        })

    # sort by revenue descending
    spo_performance.sort(key=lambda x: x['revenue'], reverse=True)

    # ── Churn Alerts ───────────────────────────────────────
    high_churn_leads = get_high_churn_leads(limit=5)

    # ── Top Scored Leads ───────────────────────────────────
    top_leads = leads.filter(
        ai_score__gt=0
    ).order_by('-ai_score')[:5]

    # ── Activity Today ─────────────────────────────────────
    meetings_today = Meeting.objects.filter(
        scheduled_at__date=today,
        status='scheduled'
    ).count()

    tasks_overdue = GeneralTask.objects.filter(
        due_date__lt=today,
        status__in=['todo', 'in_progress']
    ).count()

    tickets_open = Ticket.objects.filter(
        status__in=['open', 'in_progress']
    ).count()

    followups_today = FollowUp.objects.filter(
        follow_up_date__date=today,
        status='pending'
    ).count()

    # ── AI Forecast ────────────────────────────────────────
    forecast = generate_sales_forecast()

    context = {
        'active': 'ceo_dashboard',
        'title': 'CEO Dashboard',

        # revenue
        'total_revenue': total_revenue,
        'this_month_revenue': this_month_revenue,
        'advance_revenue': advance_revenue,
        'full_revenue': full_revenue,

        # pipeline
        'total_leads': total_leads,
        'new_leads': new_leads,
        'positive_leads': positive_leads,
        'converted_leads': converted_leads,
        'lost_leads': lost_leads,
        'quotation_leads': quotation_leads,
        'conversion_rate': conversion_rate,
        'pipeline_value': pipeline_value,

        # team
        'spo_performance': spo_performance,

        # ai
        'high_churn_leads': high_churn_leads,
        'top_leads': top_leads,
        'forecast': forecast,

        # activity
        'meetings_today': meetings_today,
        'tasks_overdue': tasks_overdue,
        'tickets_open': tickets_open,
        'followups_today': followups_today,
    }
    return render(request, 'leads/ceo_dashboard.html', context)