from django.contrib import admin
from .models import ChatSession, ChatMessage, DemoBooking


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ('direction', 'message', 'whatsapp_message_id', 'delivered', 'created_at')
    can_delete = False


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = (
        'phone_number', 'lead_name', 'is_active',
        'handed_off_to_human', 'updated_at'
    )
    list_filter = ('is_active', 'handed_off_to_human')
    search_fields = ('phone_number', 'lead_name')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ChatMessageInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'direction', 'message', 'delivered', 'created_at')
    list_filter = ('direction', 'delivered')
    search_fields = ('session__phone_number', 'message')
    readonly_fields = ('created_at',)


@admin.register(DemoBooking)
class DemoBookingAdmin(admin.ModelAdmin):
    list_display = (
        'client_name', 'company_name', 'business_type',
        'preferred_day', 'preferred_time', 'status', 'created_at'
    )
    list_filter = ('status', 'business_type')
    search_fields = ('client_name', 'company_name', 'whatsapp_number')
    readonly_fields = ('created_at', 'crm_meeting_id')