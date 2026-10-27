"""
Admin registration for Assignment Tracker models.
"""
from django.contrib import admin
from .models import Subject, Assignment


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
