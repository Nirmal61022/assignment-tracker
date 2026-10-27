"""
Custom template tags for the tracker app.
"""
from django import template
from django.utils import timezone
import datetime

register = template.Library()


@register.filter
def priority_class(priority):
    """Return CSS class for priority badge."""
    return {
        'high': 'priority-high',
        'medium': 'priority-medium',
        'low': 'priority-low',
    }.get(priority, '')


@register.filter
def status_class(assignment):
    """Return CSS class based on effective status."""
    if hasattr(assignment, 'is_overdue') and assignment.is_overdue:
        return 'status-overdue'
    return {
        'pending': 'status-pending',
        'in_progress': 'status-in-progress',
        'submitted': 'status-submitted',
    }.get(assignment.status if hasattr(assignment, 'status') else assignment, '')


@register.filter
def effective_status_label(assignment):
    if hasattr(assignment, 'is_overdue') and assignment.is_overdue:
        return 'Overdue'
    return assignment.get_status_display()


@register.simple_tag
def days_until(due_date):
    """Return number of days until due date."""
    today = timezone.localdate()
    delta = due_date - today
    return delta.days


@register.filter
def days_until_filter(due_date):
    today = timezone.localdate()
    return (due_date - today).days
