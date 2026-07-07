from django.contrib import admin
from .models import ChatSession, ChatMessage


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
    list_display = (
        'session', 'direction', 'message',
        'delivered', 'created_at'
    )
    list_filter = ('direction', 'delivered')
    search_fields = ('session__phone_number', 'message')
    readonly_fields = ('created_at',)