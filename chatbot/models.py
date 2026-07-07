from django.db import models


class ChatSession(models.Model):
    """
    One session per WhatsApp phone number.
    Stores full conversation history for AI context.
    """
    phone_number = models.CharField(max_length=20, unique=True)
    lead_name = models.CharField(max_length=150, blank=True, null=True)
    conversation_history = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    handed_off_to_human = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.phone_number} — {self.lead_name or 'Unknown'}"

    class Meta:
        ordering = ['-updated_at']


class ChatMessage(models.Model):
    """
    Every individual message sent or received.
    direction: inbound = customer → bot, outbound = bot → customer
    """
    DIRECTION_CHOICES = [
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ]

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    message = models.TextField()
    whatsapp_message_id = models.CharField(
        max_length=255, blank=True, null=True,
        help_text='Message ID returned by Meta WhatsApp Cloud API'
    )
    delivered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.direction} | {self.session.phone_number} | {self.created_at:%d %b %H:%M}"

    class Meta:
        ordering = ['created_at']