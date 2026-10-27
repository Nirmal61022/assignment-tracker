"""
Admin registration for Assignment Tracker models.
"""
from django.contrib import admin
from .models import Subject, Assignment, FAQ, ErrorCode, SupportTicket, RequestLog


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'assignment_count', 'created_at')
    list_filter = ('user',)
    search_fields = ('name', 'user__username')


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'user', 'due_date', 'priority', 'status', 'created_at')
    list_filter = ('status', 'priority', 'subject', 'user')
    search_fields = ('title', 'user__username')
    date_hierarchy = 'due_date'


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'order', 'is_active', 'created_at')
    list_filter = ('category', 'is_active')
    search_fields = ('question', 'answer')


@admin.register(ErrorCode)
class ErrorCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_custom', 'created_at')
    list_filter = ('is_custom',)
    search_fields = ('code', 'name', 'description')


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'subject', 'user', 'email', 'category', 'priority', 'status', 'created_at')
    list_filter = ('status', 'priority', 'category', 'source')
    search_fields = ('ticket_number', 'subject', 'description', 'email')


@admin.register(RequestLog)
class RequestLogAdmin(admin.ModelAdmin):
    list_display = ('method', 'path', 'status_code', 'duration_ms', 'ip_address', 'timestamp')
    list_filter = ('status_code', 'method')
    search_fields = ('path', 'ip_address')
    date_hierarchy = 'timestamp'

