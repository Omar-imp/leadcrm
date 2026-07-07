"""
Two endpoints:
  GET  /chatbot/webhook/  — Meta webhook verification
  POST /chatbot/webhook/  — Incoming WhatsApp messages from Meta
"""
import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .services.webhook import handle_incoming_message, parse_meta_payload

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def whatsapp_webhook(request):
    """
    Single endpoint for Meta WhatsApp Cloud API.

    GET  = Meta verification challenge (one-time setup)
    POST = Incoming customer messages
    """
    if request.method == 'GET':
        return _handle_verification(request)
    return _handle_incoming(request)


def _handle_verification(request):
    """
    Meta sends a GET request to verify the webhook URL.
    We must return the challenge string to confirm ownership.
    """
    mode = request.GET.get('hub.mode')
    token = request.GET.get('hub.verify_token')
    challenge = request.GET.get('hub.challenge')

    verify_token = getattr(settings, 'META_VERIFY_TOKEN', 'leadcrm123')

    if mode == 'subscribe' and token == verify_token:
        logger.info('Meta webhook verified successfully.')
        return HttpResponse(challenge, content_type='text/plain', status=200)

    logger.warning(
        'Meta webhook verification failed. '
        'Expected token: %s, received: %s', verify_token, token
    )
    return HttpResponse('Verification failed', status=403)


def _handle_incoming(request):
    """
    Processes incoming WhatsApp messages from Meta.
    Always returns 200 — Meta will retry if we return anything else.
    """
    try:
        data = json.loads(request.body)
        messages = parse_meta_payload(data)

        for phone, text in messages:
            handle_incoming_message(phone, text)

        return JsonResponse({'status': 'received'}, status=200)

    except json.JSONDecodeError:
        logger.error('Invalid JSON in Meta webhook payload.')
        return JsonResponse({'status': 'invalid json'}, status=200)

    except Exception as exc:
        logger.exception('Unexpected error in webhook handler: %s', exc)
        return JsonResponse({'status': 'error'}, status=200)