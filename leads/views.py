from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout

from .models import Lead, FollowUp, SalesPerson, Payment, ScheduledPayment, Installment
from .forms import LeadForm, FollowUpForm, PaymentForm, ScheduledPaymentForm, InstallmentForm
from django.contrib.auth.models import User
from .decorators import role_required

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


