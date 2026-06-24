from django.contrib import admin
from .models import (Lead, FollowUp, SalesPerson, Payment, 
                     ScheduledPayment, Installment, UserProfile, 
                     Company, Contact)

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display  = ('name', 'industry', 'phone', 'city', 'country')
    search_fields = ('name', 'email')
    list_filter   = ('industry',)

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display  = ('first_name', 'last_name', 'email', 'phone', 'company', 'job_title')
    search_fields = ('first_name', 'last_name', 'email')
    list_filter   = ('company',)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone')
    list_filter = ('role',)


@admin.register(SalesPerson)
class SalesPersonAdmin(admin.ModelAdmin):
    list_display = ('name', 'user')


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_number', 'lead_source', 'status', 'spo', 'created_at')
    list_filter = ('status', 'lead_source', 'spo')
    search_fields = ('name', 'contact_number', 'email')


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ('lead', 'follow_up_date', 'status')
    list_filter = ('status',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('lead', 'payment_type', 'amount', 'date')
    list_filter = ('payment_type',)

@admin.register(ScheduledPayment)
class ScheduledPaymentAdmin(admin.ModelAdmin):
    list_display = ('lead', 'total_amount', 'created_at')

@admin.register(Installment)
class InstallmentAdmin(admin.ModelAdmin):
    list_display = ('schedule', 'amount', 'due_date', 'is_paid')
    list_filter = ('is_paid',)

