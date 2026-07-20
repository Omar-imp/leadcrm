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
    path('leads/<int:pk>/delete/', views.lead_delete, name='lead_delete'),

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

    # Projects
    path('projects/', views.project_list, name='project_list'),
    path('projects/create/', views.project_create, name='project_create'),
    path('projects/create/from/<int:opp_pk>/', views.project_create, name='project_create_from_opp'),
    path('projects/<int:pk>/', views.project_detail, name='project_detail'),
    path('projects/<int:pk>/edit/', views.project_edit, name='project_edit'),
    path('projects/<int:pk>/delete/', views.project_delete, name='project_delete'),
    path('opportunities/<int:opp_pk>/convert/', views.convert_to_project, name='convert_to_project'),

    # Milestones
    path('projects/<int:project_pk>/milestones/add/', views.milestone_create, name='milestone_create'),
    path('milestones/<int:pk>/edit/', views.milestone_edit, name='milestone_edit'),
    path('milestones/<int:pk>/delete/', views.milestone_delete, name='milestone_delete'),

    # Tasks
    path('milestones/<int:milestone_pk>/tasks/add/', views.task_create, name='task_create'),
    path('tasks/<int:pk>/edit/', views.task_edit, name='task_edit'),
    path('tasks/<int:pk>/delete/', views.task_delete, name='task_delete'),
    path('tasks/<int:pk>/status/<str:status>/', views.task_status, name='task_status'),

    # Meetings
    path('meetings/', views.meeting_list, name='meeting_list'),
    path('meetings/create/', views.meeting_create, name='meeting_create'),
    path('meetings/<int:pk>/', views.meeting_detail, name='meeting_detail'),
    path('meetings/<int:pk>/edit/', views.meeting_edit, name='meeting_edit'),
    path('meetings/<int:pk>/delete/', views.meeting_delete, name='meeting_delete'),
    path('meetings/<int:pk>/status/<str:status>/', views.meeting_status, name='meeting_status'),

    # General Tasks
    path('general-tasks/', views.general_task_list, name='general_task_list'),
    path('general-tasks/create/', views.general_task_create, name='general_task_create'),
    path('general-tasks/<int:pk>/edit/', views.general_task_edit, name='general_task_edit'),
    path('general-tasks/<int:pk>/delete/', views.general_task_delete, name='general_task_delete'),
    path('general-tasks/<int:pk>/status/<str:status>/', views.general_task_status, name='general_task_status'),

    # Communication Log
    path('communications/', views.communication_list, name='communication_list'),
    path('communications/create/', views.communication_create, name='communication_create'),
    path('communications/<int:pk>/delete/', views.communication_delete, name='communication_delete'),
    path('communications/timeline/', views.communication_timeline, name='communication_timeline'),

    # Reports
    path('reports/', views.reports, name='reports'),

    # Support Tickets
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('tickets/create/', views.ticket_create, name='ticket_create'),
    path('tickets/<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('tickets/<int:pk>/edit/', views.ticket_edit, name='ticket_edit'),
    path('tickets/<int:pk>/delete/', views.ticket_delete, name='ticket_delete'),
    path('tickets/<int:pk>/status/<str:status>/', views.ticket_status, name='ticket_status'),

    # Activity Log
    path('activity/', views.activity_log, name='activity_log'),

    # Documents
    path('documents/', views.document_list, name='document_list'),
    path('documents/upload/', views.document_upload, name='document_upload'),
    path('documents/<int:pk>/delete/', views.document_delete, name='document_delete'),

    # Contracts
    path('contracts/', views.contract_list, name='contract_list'),
    path('contracts/create/', views.contract_create, name='contract_create'),
    path('contracts/<int:pk>/', views.contract_detail, name='contract_detail'),
    path('contracts/<int:pk>/edit/', views.contract_edit, name='contract_edit'),
    path('contracts/<int:pk>/delete/', views.contract_delete, name='contract_delete'),
    path('contracts/<int:pk>/status/<str:status>/', views.contract_status, name='contract_status'),

    # Notifications
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/<int:pk>/read/', views.notification_read, name='notification_read'),
    path('notifications/read-all/', views.notification_read_all, name='notification_read_all'),
    path('notifications/<int:pk>/delete/', views.notification_delete, name='notification_delete'),

    path('leads/bulk-import/', views.bulk_import_leads, name='bulk_import_leads'),
    path('whatsapp/bulk/', views.bulk_whatsapp_sender, name='bulk_whatsapp_sender'),

    path('leads/<int:pk>/score/', views.score_lead_view, name='score_lead'),
    path('leads/score-all/', views.score_all_leads, name='score_all_leads'),

    path('leads/<int:pk>/ai-assign/', views.ai_assign_lead, name='ai_assign_lead'),
    path('leads/<int:pk>/next-action/', views.next_action_view, name='next_action'),

    # Sales Persons
    path('salespersons/', views.salesperson_list, name='salesperson_list'),
    path('salespersons/create/', views.salesperson_create, name='salesperson_create'),
    path('salespersons/<int:pk>/edit/', views.salesperson_edit, name='salesperson_edit'),
    path('salespersons/<int:pk>/delete/', views.salesperson_delete, name='salesperson_delete'),

    path('leads/<int:pk>/closing-probability/', views.closing_probability_view, name='closing_probability'),
    path('leads/<int:pk>/ai-message/', views.ai_followup_message_view, name='ai_followup_message'),
    path('meetings/<int:pk>/summarize/', views.ai_meeting_summary_view, name='ai_meeting_summary'),
    path('forecast/', views.sales_forecast_view, name='sales_forecast'),

    path('leads/<int:pk>/churn-risk/', views.churn_risk_view, name='churn_risk'),
    path('leads/churn-risk/all/', views.churn_risk_all_view, name='churn_risk_all'),
    path('leads/<int:pk>/upsell/', views.upsell_recommendations_view, name='upsell_recommendations'),
    path('leads/<int:pk>/lifetime-value/', views.lifetime_value_view, name='lifetime_value'),
    path('leads/<int:pk>/360/', views.customer_360_view, name='customer_360'),
    path('ceo/', views.ceo_dashboard, name='ceo_dashboard'),

    # AI Proposal Writer
    path('proposals/', views.proposal_list, name='proposal_list'),
    path('proposals/write/', views.proposal_writer, name='proposal_writer'),
    path('proposals/write/<int:lead_pk>/', views.proposal_writer, name='proposal_writer_lead'),
    path('proposals/<int:pk>/', views.proposal_detail, name='proposal_detail'),
    path('proposals/<int:pk>/delete/', views.proposal_delete, name='proposal_delete'),

    path('assistant/config/', views.assistant_config, name='assistant_config'),
path('assistant/chat/', views.assistant_chat, name='assistant_chat'),
path('assistant/history/<int:conversation_id>/', views.assistant_history, name='assistant_history'),
]