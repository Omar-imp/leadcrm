from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('webhook/', views.whatsapp_webhook, name='whatsapp_webhook'),
]