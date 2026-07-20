from django.contrib import admin
from .models import (Lead, FollowUp, SalesPerson, Payment,
                     ScheduledPayment, Installment, UserProfile,
                     Company, Contact, Opportunity,
                     Quotation, QuotationItem,
                     Project, Milestone, Task,
                     Meeting, GeneralTask, CommunicationLog,
                     Ticket, TicketReply, ActivityLog, 
                     Document, Contract, Notification, Proposal)


from django.contrib import admin
from .models import AssistantPermission

@admin.register(AssistantPermission)
class AssistantPermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'crm_assistant', 'sales_assistant')
    

@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ('title', 'lead', 'status', 'created_by', 'created_at')
    list_filter = ('status',)
    search_fields = ('title',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notif_type', 'is_read', 'created_at')
    list_filter  = ('notif_type', 'is_read')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'doc_type', 'uploaded_by', 'created_at')
    list_filter = ('doc_type',)


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'entity_type', 'entity_name', 'user', 'created_at')
    list_filter = ('action', 'entity_type')
    search_fields = ('description', 'entity_name')
    readonly_fields = ('user', 'action', 'entity_type', 'entity_id',
                       'entity_name', 'description', 'created_at')


@admin.register(SalesPerson)
class SalesPersonAdmin(admin.ModelAdmin):
    list_display = ('name', 'user')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone')
    list_filter = ('role',)


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


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'industry', 'phone', 'city', 'country')
    search_fields = ('name', 'email')
    list_filter = ('industry',)


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone', 'company', 'job_title')
    search_fields = ('first_name', 'last_name', 'email')
    list_filter = ('company',)


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ('title', 'stage', 'value', 'probability', 'assigned_to', 'expected_close_date')
    list_filter = ('stage', 'priority')
    search_fields = ('title',)


class QuotationItemInline(admin.TabularInline):
    model = QuotationItem
    extra = 1


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'company', 'valid_until', 'created_at')
    list_filter = ('status',)
    search_fields = ('title',)
    inlines = [QuotationItemInline]


class MilestoneInline(admin.TabularInline):
    model = Milestone
    extra = 1


class TaskInline(admin.TabularInline):
    model = Task
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'priority', 'manager', 'start_date', 'end_date')
    list_filter = ('status', 'priority', 'methodology')
    search_fields = ('name',)
    inlines = [MilestoneInline]


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'status', 'start_date', 'end_date')
    list_filter = ('status',)
    inlines = [TaskInline]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'milestone', 'assigned_to', 'status', 'priority', 'due_date')
    list_filter = ('status', 'priority')


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ('title', 'meeting_type', 'status', 'scheduled_at', 'created_by')
    list_filter = ('status', 'meeting_type')
    search_fields = ('title',)


@admin.register(GeneralTask)
class GeneralTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'priority', 'assigned_to', 'due_date')
    list_filter = ('status', 'priority')


@admin.register(CommunicationLog)
class CommunicationLogAdmin(admin.ModelAdmin):
    list_display = ('comm_type', 'direction', 'subject', 'created_by', 'created_at')
    list_filter = ('comm_type', 'direction')
    search_fields = ('subject', 'body')


class TicketReplyInline(admin.TabularInline):
    model = TicketReply
    extra = 1


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'priority', 'category', 'assigned_to', 'created_at')
    list_filter = ('status', 'priority', 'category')
    search_fields = ('title', 'description')
    inlines = [TicketReplyInline]


@admin.register(TicketReply)
class TicketReplyAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'author', 'created_at')


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'company', 'value', 'start_date', 'end_date')
    list_filter = ('status',)
    search_fields = ('title',)