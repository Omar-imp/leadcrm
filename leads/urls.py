from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Users
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),

    # Companies
    path('companies/', views.company_list, name='company_list'),
    path('companies/create/', views.company_create, name='company_create'),
    path('companies/<int:pk>/', views.company_detail, name='company_detail'),
    path('companies/<int:pk>/edit/', views.company_edit, name='company_edit'),
    path('companies/<int:pk>/delete/', views.company_delete, name='company_delete'),

    # Contacts
    path('contacts/', views.contact_list, name='contact_list'),
    path('contacts/create/', views.contact_create, name='contact_create'),
    path('contacts/<int:pk>/edit/', views.contact_edit, name='contact_edit'),
    path('contacts/<int:pk>/delete/', views.contact_delete, name='contact_delete'),

    # Leads
    path('leads/create/', views.create_lead, name='create_lead'),
    path('leads/', views.lead_list, name='all_leads'),
    path('leads/status/<str:status>/', views.lead_list, name='lead_status_list'),
    path('leads/<int:pk>/', views.lead_detail, name='lead_detail'),
    path('leads/<int:pk>/status/<str:status>/', views.update_lead_status, name='update_lead_status'),
    path('leads/<int:pk>/payment/add/', views.add_payment, name='add_payment'),

    # Followups
    path('followups/<str:scope>/', views.followup_list, name='followup_list'),
    path('followups/<int:pk>/done/', views.followup_done, name='followup_done'),

    # Payments
    path('payments/advance/', views.payment_list, {'ptype': 'advance'}, name='payment_advance'),
    path('payments/full/', views.payment_list, {'ptype': 'full'}, name='payment_full'),
    path('payments/scheduled/', views.scheduled_payment_list, name='scheduled_payment_list'),
    path('payments/scheduled/create/', views.scheduled_payment_create, name='scheduled_payment_create'),
    path('payments/scheduled/<int:pk>/', views.scheduled_payment_detail, name='scheduled_payment_detail'),

    # Pipeline / Opportunities
    path('pipeline/', views.opportunity_pipeline, name='opportunity_pipeline'),
    path('opportunities/', views.opportunity_list, name='opportunity_list'),
    path('opportunities/create/', views.opportunity_create, name='opportunity_create'),
    path('opportunities/<int:pk>/', views.opportunity_detail, name='opportunity_detail'),
    path('opportunities/<int:pk>/edit/', views.opportunity_edit, name='opportunity_edit'),
    path('opportunities/<int:pk>/delete/', views.opportunity_delete, name='opportunity_delete'),
    path('opportunities/<int:pk>/move/<str:stage>/', views.opportunity_move, name='opportunity_move'),

    # Quotations
    path('quotations/', views.quotation_list, name='quotation_list'),
    path('quotations/create/', views.quotation_create, name='quotation_create'),
    path('quotations/<int:pk>/', views.quotation_detail, name='quotation_detail'),
    path('quotations/<int:pk>/edit/', views.quotation_edit, name='quotation_edit'),
    path('quotations/<int:pk>/delete/', views.quotation_delete, name='quotation_delete'),
    path('quotations/<int:pk>/status/<str:status>/', views.quotation_status, name='quotation_status'),
]