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

    path('followups/<str:scope>/', views.followup_list, name='followup_list'),
    path('followups/<int:pk>/done/', views.followup_done, name='followup_done'),
]