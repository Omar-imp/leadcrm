from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('leads/create/', views.create_lead, name='create_lead'),
    path('leads/', views.lead_list, name='all_leads'),
    path('leads/status/<str:status>/', views.lead_list, name='lead_status_list'),
    path('leads/<int:pk>/', views.lead_detail, name='lead_detail'),
    path('leads/<int:pk>/status/<str:status>/', views.update_lead_status, name='update_lead_status'),
    path('leads/<int:pk>/payment/add/', views.add_payment, name='add_payment'),

    path('followups/<str:scope>/', views.followup_list, name='followup_list'),
    path('followups/<int:pk>/done/', views.followup_done, name='followup_done'),

    path('payments/advance/', views.payment_list, {'ptype': 'advance'}, name='payment_advance'),
    path('payments/full/', views.payment_list, {'ptype': 'full'}, name='payment_full'),
    path('payments/scheduled/', views.scheduled_payment_list, name='scheduled_payment_list'),
    path('payments/scheduled/create/', views.scheduled_payment_create, name='scheduled_payment_create'),
    path('payments/scheduled/<int:pk>/', views.scheduled_payment_detail, name='scheduled_payment_detail'),

    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
]