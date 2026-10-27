"""
URL routes for Assignment Tracker app.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Root
    path('', views.index, name='index'),

    # Auth
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Assignments
    path('assignments/', views.assignment_list, name='assignment_list'),
    path('assignments/new/', views.assignment_create, name='assignment_create'),
    path('assignments/<int:pk>/', views.assignment_detail, name='assignment_detail'),
    path('assignments/<int:pk>/edit/', views.assignment_edit, name='assignment_edit'),
    path('assignments/<int:pk>/delete/', views.assignment_delete, name='assignment_delete'),
    path('assignments/<int:pk>/submit/', views.assignment_mark_submitted, name='assignment_submit'),

    # Subjects
    path('subjects/', views.subject_list, name='subject_list'),
    path('subjects/new/', views.subject_create, name='subject_create'),
    path('subjects/<int:pk>/edit/', views.subject_edit, name='subject_edit'),
    path('subjects/<int:pk>/delete/', views.subject_delete, name='subject_delete'),

    # Calendar
    path('calendar/', views.calendar_view, name='calendar'),

    # FAQs & Error Codes (SQL Database)
    path('faqs/', views.faq_list, name='faq_list'),
    path('error-codes/', views.error_code_list, name='error_code_list'),

    # Support Tickets (SQL Database)
    path('tickets/', views.ticket_list, name='ticket_list'),

    # Health Check & Diagnostics
    path('health/', views.health_check, name='health_check'),

    # AI Assistant APIs & MongoDB Logging
    path('api/chat/', views.api_chat, name='api_chat'),
    path('api/tickets/create/', views.api_ticket_create, name='api_ticket_create'),
    path('api/feedback/', views.api_feedback, name='api_feedback'),
    path('api/motivation/', views.api_motivation, name='api_motivation'),

    # Error Page Demos
    path('test-404/', views.test_404_view, name='test_404'),
    path('test-500/', views.test_500_view, name='test_500'),
]
