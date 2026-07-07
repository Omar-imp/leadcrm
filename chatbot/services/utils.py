"""
Shared utility functions for the chatbot app.
Phone number normalization and basic helpers.
"""
import re


def normalize_phone(phone: str) -> str:
    """
    Converts any phone number to E.164 format required by Meta WhatsApp Cloud API.

    Examples:
        03001234567     → +923001234567  (Pakistan local)
        923001234567    → +923001234567  (no plus)
        +923001234567   → +923001234567  (already correct)
        00923001234567  → +923001234567  (international prefix 00)
        971501234567    → +971501234567  (UAE)
    """
    if not phone:
        return ''

    cleaned = re.sub(r'[^\d+]', '', str(phone).strip())

    if cleaned.startswith('+'):
        return cleaned

    if cleaned.startswith('00'):
        return '+' + cleaned[2:]

    # Pakistani local number (starts with 0, 11 digits total)
    if cleaned.startswith('0') and len(cleaned) == 11:
        return '+92' + cleaned[1:]

    # already has country code without +
    if len(cleaned) >= 11:
        return '+' + cleaned

    return '+' + cleaned


def is_valid_phone(phone: str) -> bool:
    """Returns True if the number looks like a valid E.164 number."""
    normalized = normalize_phone(phone)
    return bool(re.match(r'^\+\d{10,15}$', normalized))


def truncate_message(text: str, max_length: int = 4096) -> str:
    """
    Truncates text to WhatsApp's maximum message length.
    Meta WhatsApp Cloud API limit is 4096 characters.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + '...'