from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render


def login_selector(request):
    return render(request, 'login_selector.html')


urlpatterns = [
    path('', login_selector, name='login_selector'),
    path('admin/', admin.site.urls),
    path('leadcrm/', include('leads.urls')),
    path('ecommerce/', include('ecommerce.urls')),
    path('chatbot/', include('chatbot.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)