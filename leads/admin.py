from django.contrib import admin
from .models import Lead, FollowUp, SalesPerson


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