from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout
from .forms import LeadForm, FollowUpForm, PaymentForm, ScheduledPaymentForm, InstallmentForm
from django.contrib.auth.models import User
from .decorators import role_required
from .models import (Lead, FollowUp, SalesPerson, Payment,
                     ScheduledPayment, Installment, UserProfile,
                     Company, Contact, Opportunity,
                     Quotation, QuotationItem,
                     OPPORTUNITY_STAGE_CHOICES, PRIORITY_CHOICES,
                     QUOTATION_STATUS_CHOICES, ROLE_CHOICES)


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
def create_lead(request):
    if request.method == 'POST':
        form = LeadForm(request.POST)
        if form.is_valid():
            lead = form.save(commit=False)
            if hasattr(request.user, 'salesperson'):
                lead.spo = request.user.salesperson
            lead.save()
            messages.success(request, 'Lead created successfully.')
            return redirect('all_leads')
    else:
        form = LeadForm()
    spo_name = None
    if hasattr(request.user, 'salesperson'):
        spo_name = request.user.salesperson.name
    return render(request, 'leads/lead_form.html', {'form': form, 'active': 'create_lead', 'spo_name': spo_name})


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
def update_lead_status(request, pk, status):
    lead = get_object_or_404(Lead, pk=pk)
    valid_statuses = dict(Lead._meta.get_field('status').choices)
    if status in valid_statuses:
        lead.status = status
        lead.save()
        messages.success(request, f'Lead marked as {valid_statuses[status]}.')
    return redirect(request.META.get('HTTP_REFERER', 'all_leads'))


@login_required
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

    context = {
        'lead': lead,
        'followup_form': followup_form,
        'followups': lead.followups.all(),
        'active': 'all_leads',
    }
    return render(request, 'leads/lead_detail.html', context)


@login_required
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

@login_required
@role_required('admin')
def user_list(request):
    # Build a safe list of users and their profiles (profile may be missing)
    users_qs = User.objects.all().order_by('username')
    users_safe = []
    for u in users_qs:
        try:
            profile = u.profile
        except Exception:
            profile = None
        users_safe.append({'user': u, 'profile': profile})

    context = {'users': users_safe, 'active': 'users', 'title': 'Users'}
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
            user = User.objects.create_user(username=username, email=email, password=password)
            user.profile.role = role
            user.profile.phone = phone
            user.profile.save()
            messages.success(request, f'User {username} created successfully.')
            return redirect('user_list')

    from .models import ROLE_CHOICES
    return render(request, 'leads/user_form.html', {
        'active': 'users',
        'title': 'Create User',
        'role_choices': ROLE_CHOICES,
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
        messages.success(request, 'User updated.')
        return redirect('user_list')

    from .models import ROLE_CHOICES
    return render(request, 'leads/user_form.html', {
        'active': 'users',
        'title': 'Edit User',
        'edit_user': user,
        'role_choices': ROLE_CHOICES,
    })


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
def opportunity_delete(request, pk):
    opp = get_object_or_404(Opportunity, pk=pk)
    opp.delete()
    messages.success(request, 'Opportunity deleted.')
    return redirect('opportunity_pipeline')


@login_required
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
def quotation_delete(request, pk):
    quotation = get_object_or_404(Quotation, pk=pk)
    quotation.delete()
    messages.success(request, 'Quotation deleted.')
    return redirect('quotation_list')


@login_required
def quotation_status(request, pk, status):
    quotation = get_object_or_404(Quotation, pk=pk)
    valid = dict(QUOTATION_STATUS_CHOICES)
    if status in valid:
        quotation.status = status
        quotation.save()
        messages.success(request, f'Quotation marked as {valid[status]}.')
    return redirect('quotation_detail', pk=pk)