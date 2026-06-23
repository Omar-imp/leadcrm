from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class SalesPerson(models.Model):
    """SPO - Sales Person Officer assigned to leads,"""
    name = models.CharField(max_length=100)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null = True, blank = True)

    def __str__(self):
        return self.name
    

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


class FollowUp(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('done', 'Done')
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