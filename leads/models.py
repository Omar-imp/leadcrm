from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class SalesPerson(models.Model):
    """SPO - Sales Person Officer assigned to leads,"""
    name = models.CharField(max_length=100)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null = True, blank = True)

    def __str__(self):
        return self.name

ROLE_CHOICES = [
    ('admin', 'Admin'),
    ('sales_manager', 'Sales Manager'),
    ('sales_executive', 'Sales Executive'),
    ('project_manager', 'Project Manager'),
    ('finance', 'Finance'),
    ('support_agent', 'Support Agent'),
    ('ceo', 'CEO'),
]


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='sales_executive')
    phone = models.CharField(max_length=30, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"    

LEAD_SOURCE_CHOICES = [
    ('advertisement', 'Advertisement'),
    ('landline', 'Landline'),
    ('direct_call', 'Direct Call'),
    ('facebook', 'Facebook'),
    ('whatsapp', 'Whatsapp'),
    ('website', 'Website'),
    ('personal_reference', 'Personal Reference'),
    ('client_reference', 'Client Reference'),
    ('staff_reference', 'Staff Reference'),
    ('email', 'Email'),
    ('walkin', 'Walkin'),
]

LEAD_STATUS_CHOICES = [
    ('new', 'New'),
    ('positive', 'Positive'),
    ('lost', 'Lost'),
    ('quotation', 'Quotation'),
    ('converted', 'Converted'),
]

class Lead(models.Model):
    lead_source    = models.CharField(max_length=30, choices=LEAD_SOURCE_CHOICES, default='advertisement')
    name           = models.CharField(max_length=150)
    contact_number = models.CharField(max_length=30)
    email          = models.EmailField(blank=True, null=True)
    country        = models.CharField(max_length=100, blank=True, null=True)
    city           = models.CharField(max_length=100, blank=True, null=True)
    address        = models.CharField(max_length=225, blank=True, null=True)
    quotation      = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    detail         = models.TextField(blank=True, null=True)
    status         = models.CharField(max_length=20, choices=LEAD_STATUS_CHOICES, default='new')
    spo            = models.ForeignKey(SalesPerson, on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    created_at     = models.DateTimeField(default=timezone.now)
    updated_at     = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    class Meta:
        ordering = ['-created_at']

INDUSTRY_CHOICES = [
    ('technology', 'Technology'),
    ('finance', 'Finance'),
    ('healthcare', 'Healthcare'),
    ('education', 'Education'),
    ('retail', 'Retail'),
    ('manufacturing', 'Manufacturing'),
    ('real_estate', 'Real Estate'),
    ('construction', 'Construction'),
    ('marketing', 'Marketing'),
    ('other', 'Other'),
]


class Company(models.Model):
    name = models.CharField(max_length=200)
    industry = models.CharField(max_length=30, choices=INDUSTRY_CHOICES, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Companies'


class Contact(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    job_title = models.CharField(max_length=100, blank=True, null=True)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='contacts')
    lead = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True, blank=True, related_name='contacts')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name or ''}".strip()

    def get_full_name(self):
        return f"{self.first_name} {self.last_name or ''}".strip()

    class Meta:
        ordering = ['first_name']

OPPORTUNITY_STAGE_CHOICES = [
    ('new', 'New'),
    ('contacted', 'Contacted'),
    ('qualified', 'Qualified'),
    ('proposal', 'Proposal Sent'),
    ('negotiation', 'Negotiation'),
    ('won', 'Won'),
    ('lost', 'Lost'),
]

PRIORITY_CHOICES = [
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High')
]

class Opportunity(models.Model):
    title               = models.CharField(max_length=200)
    lead                = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True, blank=True, related_name='opportunities')
    contact             = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name='opportunities')
    company             = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='opportunities')
    assigned_to         = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='opportunities')
    stage               = models.CharField(max_length=20, choices=OPPORTUNITY_STAGE_CHOICES, default='new')
    priority            = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    value               = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    probability         = models.IntegerField(default=0, help_text='Win probability 0-100%')
    expected_close_date = models.DateField(blank=True, null=True)
    description         = models.TextField(blank=True, null=True)
    lost_reason         = models.TextField(blank=True, null=True)
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Opportunities'

QUOTATION_STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('sent', 'Sent'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
]


class Quotation(models.Model):
    opportunity = models.ForeignKey(Opportunity, on_delete=models.SET_NULL, null=True, blank=True, related_name='quotations')
    lead = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True, blank=True, related_name='quotations')
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='quotations')
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name='quotations')
    title = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=QUOTATION_STATUS_CHOICES, default='draft')
    valid_until = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    terms = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='quotations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    def total_amount(self):
        return sum(item.total_price() for item in self.items.all())

    class Meta:
        ordering = ['-created_at']


class QuotationItem(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def total_price(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return self.description

PROJECT_STATUS_CHOICES = [
    ('planning', 'Planning'),
    ('active', 'Active'),
    ('on_hold', 'On Hold'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
]

PROJECT_PRIORITY_CHOICES = [
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
    ('critical', 'Critical'),
]

METHODOLOGY_CHOICES = [
    ('agile', 'Agile'),
    ('waterfall', 'Waterfall'),
    ('hybrid', 'Hybrid'),
]

MILESTONE_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('in_progress', 'In Progress'),
    ('completed', 'Completed'),
]

TASK_STATUS_CHOICES = [
    ('todo', 'To Do'),
    ('in_progress', 'In Progress'),
    ('review', 'In Review'),
    ('done', 'Done'),
]

TASK_PRIORITY_CHOICES = [
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
    ('critical', 'Critical'),
]


class Project(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    opportunity = models.OneToOneField(
        Opportunity, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='project'
    )
    company = models.ForeignKey(
        Company, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='projects'
    )
    contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='projects'
    )
    manager = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='managed_projects'
    )
    team = models.ManyToManyField(
        User, blank=True, related_name='projects'
    )
    status = models.CharField(max_length=20, choices=PROJECT_STATUS_CHOICES, default='planning')
    priority = models.CharField(max_length=10, choices=PROJECT_PRIORITY_CHOICES, default='medium')
    methodology = models.CharField(max_length=10, choices=METHODOLOGY_CHOICES, default='agile')
    budget = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    estimated_hours = models.IntegerField(default=0)
    technology_stack = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def progress(self):
        total = Task.objects.filter(milestone__project=self).count()
        if total == 0:
            return 0
        done = Task.objects.filter(milestone__project=self, status='done').count()
        return int((done / total) * 100)

    def total_tasks(self):
        return Task.objects.filter(milestone__project=self).count()

    def done_tasks(self):
        return Task.objects.filter(milestone__project=self, status='done').count()

    def pending_tasks(self):
        return Task.objects.filter(
            milestone__project=self
        ).exclude(status='done').count()

    class Meta:
        ordering = ['-created_at']


class Milestone(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='milestones'
    )
    status = models.CharField(max_length=15, choices=MILESTONE_STATUS_CHOICES, default='pending')
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    order = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.project.name} — {self.title}"

    def progress(self):
        total = self.tasks.count()
        if total == 0:
            return 0
        done = self.tasks.filter(status='done').count()
        return int((done / total) * 100)

    class Meta:
        ordering = ['order', 'start_date']


class Task(models.Model):
    milestone = models.ForeignKey(Milestone, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='tasks'
    )
    status = models.CharField(max_length=15, choices=TASK_STATUS_CHOICES, default='todo')
    priority = models.CharField(max_length=10, choices=TASK_PRIORITY_CHOICES, default='medium')
    due_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['due_date', 'priority']

MEETING_STATUS_CHOICES = [
    ('scheduled', 'Scheduled'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
    ('no_show', 'No Show'),
]

MEETING_TYPE_CHOICES = [
    ('call', 'Phone Call'),
    ('video', 'Video Call'),
    ('in_person', 'In Person'),
    ('demo', 'Demo'),
    ('follow_up', 'Follow Up'),
]

GENERAL_TASK_STATUS_CHOICES = [
    ('todo', 'To Do'),
    ('in_progress', 'In Progress'),
    ('done', 'Done'),
]

GENERAL_TASK_PRIORITY_CHOICES = [
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
]


class Meeting(models.Model):
    title = models.CharField(max_length=200)
    meeting_type = models.CharField(max_length=20, choices=MEETING_TYPE_CHOICES, default='call')
    status = models.CharField(max_length=20, choices=MEETING_STATUS_CHOICES, default='scheduled')
    scheduled_at = models.DateTimeField()
    duration_minutes = models.IntegerField(default=30)
    location = models.CharField(max_length=255, blank=True, null=True)
    agenda = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    action_items = models.TextField(blank=True, null=True)
    lead = models.ForeignKey(
        Lead, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='meetings'
    )
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='meetings'
    )
    company = models.ForeignKey(
        Company, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='meetings'
    )
    contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='meetings'
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_meetings'
    )
    attendees = models.ManyToManyField(
        User, blank=True, related_name='meetings'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} — {self.scheduled_at:%d %b %Y %H:%M}"

    class Meta:
        ordering = ['-scheduled_at']


class GeneralTask(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='general_tasks'
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_tasks'
    )
    status = models.CharField(
        max_length=15,
        choices=GENERAL_TASK_STATUS_CHOICES,
        default='todo'
    )
    priority = models.CharField(
        max_length=10,
        choices=GENERAL_TASK_PRIORITY_CHOICES,
        default='medium'
    )
    due_date = models.DateField(blank=True, null=True)
    lead = models.ForeignKey(
        Lead, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='general_tasks'
    )
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='general_tasks'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['due_date', '-created_at']

COMMUNICATION_TYPE_CHOICES = [
    ('email', 'Email'),
    ('call', 'Phone Call'),
    ('whatsapp', 'WhatsApp'),
    ('sms', 'SMS'),
    ('note', 'Internal Note'),
    ('meeting_note', 'Meeting Note'),
]

COMMUNICATION_DIRECTION_CHOICES = [
    ('inbound', 'Inbound'),
    ('outbound', 'Outbound'),
    ('internal', 'Internal'),
]


class CommunicationLog(models.Model):
    comm_type = models.CharField(max_length=20, choices=COMMUNICATION_TYPE_CHOICES, default='note')
    direction = models.CharField(max_length=10, choices=COMMUNICATION_DIRECTION_CHOICES, default='outbound')
    subject = models.CharField(max_length=255, blank=True, null=True)
    body = models.TextField()
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='communications'
    )
    lead = models.ForeignKey(
        Lead, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='communications'
    )
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='communications'
    )
    contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='communications'
    )
    company = models.ForeignKey(
        Company, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='communications'
    )
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='communications'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_comm_type_display()} — {self.created_at:%d %b %Y}"

    class Meta:
        ordering = ['-created_at']

TICKET_STATUS_CHOICES = [
    ('open', 'Open'),
    ('in_progress', 'In Progress'),
    ('waiting', 'Waiting on Client'),
    ('resolved', 'Resolved'),
    ('closed', 'Closed'),
]

TICKET_PRIORITY_CHOICES = [
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
    ('critical', 'Critical'),
]

TICKET_CATEGORY_CHOICES = [
    ('bug', 'Bug Report'),
    ('feature', 'Feature Request'),
    ('support', 'General Support'),
    ('billing', 'Billing'),
    ('other', 'Other'),
]


class Ticket(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=TICKET_STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=10, choices=TICKET_PRIORITY_CHOICES, default='medium')
    category = models.CharField(max_length=20, choices=TICKET_CATEGORY_CHOICES, default='support')
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_tickets'
    )
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_tickets'
    )
    lead = models.ForeignKey(
        Lead, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='tickets'
    )
    company = models.ForeignKey(
        Company, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='tickets'
    )
    contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='tickets'
    )
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='tickets'
    )
    resolved_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"#{self.pk} {self.title}"

    class Meta:
        ordering = ['-created_at']


class TicketReply(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ticket_replies'
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reply to #{self.ticket.pk} by {self.author}"

    class Meta:
        ordering = ['created_at']

class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('deleted', 'Deleted'),
        ('status_changed', 'Status Changed'),
        ('assigned', 'Assigned'),
        ('commented', 'Commented'),
        ('payment', 'Payment Recorded'),
        ('converted', 'Converted'),
        ('login', 'Logged In'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='activity_logs'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    entity_type = models.CharField(max_length=50)
    entity_id = models.IntegerField(null=True, blank=True)
    entity_name = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} — {self.action} — {self.entity_type}"

    class Meta:
        ordering = ['-created_at']

class FollowUp(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('done', 'Done'),
    ]
    
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='followups')
    follow_up_date= models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Followup for {self.lead.name} on {self.follow_up_date:%Y-%m-%d}"
    
    class Meta:
        ordering = ['follow_up_date']

PAYMENT_TYPE_CHOICES = [
    ('advance', 'Advance'),
    ('full', 'Full'),
]

class Payment(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='payments')
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateTimeField(default=timezone.now)
    notes = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.get_payment_type_display()} - {self.amount} for {self.lead.name}"

    class Meta:
        ordering = ['-date']

class ScheduledPayment(models.Model):
    """A payment plan for a lead broken into installments."""
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='scheduled_payments')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Payment Plan for {self.lead.name} - Total: {self.total_amount}"

    def amount_paid(self):
        return sum(i.amount for i in self.installments.filter(is_paid=True))

    def amount_remaining(self):
        return self.total_amount - self.amount_paid()

    def next_due(self):
        return self.installments.filter(is_paid=False).order_by('due_date').first()
    
    class Meta:
        ordering = ['-created_at']


class Installment(models.Model):
    schedule  = models.ForeignKey(ScheduledPayment, on_delete=models.CASCADE, related_name='installments')
    amount    = models.DecimalField(max_digits=12, decimal_places=2)
    due_date  = models.DateField()
    is_paid   = models.BooleanField(default=False)
    paid_date = models.DateField(blank=True, null=True)
    notes     = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Installment of {self.amount} due {self.due_date}"
    
    class Meta:
        ordering = ['due_date']

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

# ── Auto-create UserProfile ────────────────────────────────
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


# ── Activity Log helpers ───────────────────────────────────
def log_activity(user, action, entity_type, entity_id, entity_name, description):
    ActivityLog.objects.create(
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        description=description,
    )

DOCUMENT_TYPE_CHOICES = [
    ('proposal', 'Proposal'),
    ('contract', 'Contract'),
    ('invoice', 'Invoice'),
    ('requirement', 'Requirement Document'),
    ('design', 'Design File'),
    ('report', 'Report'),
    ('other', 'Other'),
]


class Document(models.Model):
    title = models.CharField(max_length=200)
    doc_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES, default='other')
    file = models.FileField(upload_to='documents/%Y/%m/')
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='documents'
    )
    lead = models.ForeignKey(
        Lead, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='documents'
    )
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='documents'
    )
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='documents'
    )
    ticket = models.ForeignKey(
        Ticket, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='documents'
    )
    quotation = models.ForeignKey(
        Quotation, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='documents'
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def filename(self):
        import os
        return os.path.basename(self.file.name)

    def filesize(self):
        try:
            size = self.file.size
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size // 1024} KB"
            else:
                return f"{size // (1024 * 1024)} MB"
        except Exception:
            return "Unknown"

    class Meta:
        ordering = ['-created_at']

CONTRACT_STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('sent', 'Sent to Client'),
    ('signed', 'Signed'),
    ('active', 'Active'),
    ('expired', 'Expired'),
    ('cancelled', 'Cancelled'),
]


class Contract(models.Model):
    title = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=CONTRACT_STATUS_CHOICES, default='draft')
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='contracts'
    )
    quotation = models.ForeignKey(
        Quotation, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='contracts'
    )
    company = models.ForeignKey(
        Company, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='contracts'
    )
    contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='contracts'
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='contracts'
    )
    value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    signed_date = models.DateField(blank=True, null=True)
    terms = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    signed_file = models.FileField(
        upload_to='contracts/%Y/%m/',
        blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    class Meta:
        ordering = ['-created_at']


class Notification(models.Model):
    NOTIF_TYPE_CHOICES = [
        ('followup_due', 'Follow Up Due'),
        ('meeting_today', 'Meeting Today'),
        ('task_overdue',  'Task Overdue'),
        ('ticket_assigned', 'Ticket Assigned'),
        ('lead_assigned', 'Lead Assigned'),
        ('payment_received', 'Payment_received'),
        ('contract_signed', 'Project Update'),
        ('general', 'General'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='notifications'
    )
    notif_type = models.CharField(max_length=30, choices=NOTIF_TYPE_CHOICES, default='general')
    title      = models.CharField(max_length=200)
    message    = models.TextField()
    link       = models.CharField(max_length=255, blank=True, null=True)
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    class Meta:
        ordering = ['-created_at']

# ── Lead signals ───────────────────────────────────────────
@receiver(post_save, sender=Lead)
def log_lead_save(sender, instance, created, **kwargs):
    action = 'created' if created else 'updated'
    description = f'Lead "{instance.name}" was {action}.'
    log_activity(None, action, 'Lead', instance.pk, instance.name, description)


# ── Opportunity signals ────────────────────────────────────
@receiver(post_save, sender=Opportunity)
def log_opportunity_save(sender, instance, created, **kwargs):
    action = 'created' if created else 'updated'
    description = f'Opportunity "{instance.title}" was {action} — Stage: {instance.get_stage_display()}.'
    log_activity(None, action, 'Opportunity', instance.pk, instance.title, description)


# ── Ticket signals ─────────────────────────────────────────
@receiver(post_save, sender=Ticket)
def log_ticket_save(sender, instance, created, **kwargs):
    action = 'created' if created else 'updated'
    description = f'Ticket #{instance.pk} "{instance.title}" was {action} — Status: {instance.get_status_display()}.'
    log_activity(None, action, 'Ticket', instance.pk, instance.title, description)


# ── Payment signals ────────────────────────────────────────
@receiver(post_save, sender=Payment)
def log_payment_save(sender, instance, created, **kwargs):
    if created:
        description = f'{instance.get_payment_type_display()} payment of {instance.amount} recorded for "{instance.lead.name}".'
        log_activity(None, 'payment', 'Payment', instance.pk, str(instance.amount), description)


# ── Project signals ────────────────────────────────────────
@receiver(post_save, sender=Project)
def log_project_save(sender, instance, created, **kwargs):
    action = 'created' if created else 'updated'
    description = f'Project "{instance.name}" was {action} — Status: {instance.get_status_display()}.'
    log_activity(None, action, 'Project', instance.pk, instance.name, description)


# ── FollowUp signals ───────────────────────────────────────
@receiver(post_save, sender=FollowUp)
def log_followup_save(sender, instance, created, **kwargs):
    if created:
        description = f'Follow-up scheduled for lead "{instance.lead.name}" on {instance.follow_up_date:%d %b %Y}.'
        log_activity(None, 'created', 'FollowUp', instance.pk, instance.lead.name, description)


# ── Meeting signals ────────────────────────────────────────
@receiver(post_save, sender=Meeting)
def log_meeting_save(sender, instance, created, **kwargs):
    if created:
        try:
            scheduled = instance.scheduled_at.strftime('%d %b %Y %H:%M')
        except Exception:
            scheduled = str(instance.scheduled_at)
        description = f'Meeting "{instance.title}" scheduled for {scheduled}.'
        log_activity(None, 'created', 'Meeting', instance.pk, instance.title, description)