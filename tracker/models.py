"""
Models for Assignment Tracker app.
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Subject(models.Model):
    """A subject/course that assignments belong to."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subjects')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    color = models.CharField(max_length=7, default='#6366f1')  # Hex color for UI
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ('user', 'name')
        indexes = [
            models.Index(fields=['user', 'name']),
        ]

    def __str__(self):
        return self.name

    @property
    def assignment_count(self):
        return self.assignments.count()

    @property
    def pending_count(self):
        return self.assignments.filter(status__in=['pending', 'in_progress']).count()


class Assignment(models.Model):
    """An assignment with deadline, priority and status tracking."""

    PRIORITY_LOW = 'low'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_HIGH = 'high'
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Low'),
        (PRIORITY_MEDIUM, 'Medium'),
        (PRIORITY_HIGH, 'High'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_SUBMITTED = 'submitted'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_SUBMITTED, 'Submitted'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=300)
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name='assignments')
    description = models.TextField(blank=True, default='')
    due_date = models.DateField()
    due_time = models.TimeField(null=True, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_PENDING)
    submitted_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date', 'due_time']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'due_date']),
            models.Index(fields=['user', 'subject']),
        ]

    def __str__(self):
        return f"{self.title} ({self.subject.name})"

    @property
    def is_overdue(self):
        """Returns True if the assignment is past due and not submitted."""
        if self.status == self.STATUS_SUBMITTED:
            return False
        now = timezone.now()
        if self.due_time:
            import datetime
            due_datetime = timezone.make_aware(
                datetime.datetime.combine(self.due_date, self.due_time),
                timezone.get_current_timezone()
            )
        else:
            import datetime
            # Treat end of day as deadline if no time specified
            due_datetime = timezone.make_aware(
                datetime.datetime.combine(self.due_date, datetime.time(23, 59, 59)),
                timezone.get_current_timezone()
            )
        return now > due_datetime

    @property
    def effective_status(self):
        """Returns 'overdue' if past due and not submitted, otherwise the stored status."""
        if self.is_overdue:
            return 'overdue'
        return self.status

    @property
    def due_soon(self):
        """Returns True if due within 48 hours and not submitted."""
        if self.status == self.STATUS_SUBMITTED or self.is_overdue:
            return False
        from datetime import timedelta
        now = timezone.now()
        import datetime
        if self.due_time:
            due_datetime = timezone.make_aware(
                datetime.datetime.combine(self.due_date, self.due_time),
                timezone.get_current_timezone()
            )
        else:
            due_datetime = timezone.make_aware(
                datetime.datetime.combine(self.due_date, datetime.time(23, 59, 59)),
                timezone.get_current_timezone()
            )
        return now <= due_datetime <= now + timedelta(hours=48)

    def mark_submitted(self):
        """Mark this assignment as submitted and record the timestamp."""
        self.status = self.STATUS_SUBMITTED
        self.submitted_at = timezone.now()
        self.save(update_fields=['status', 'submitted_at', 'updated_at'])
