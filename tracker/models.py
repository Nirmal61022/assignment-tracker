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


class FAQ(models.Model):
    """Frequently Asked Question stored in SQL database."""
    CATEGORY_CHOICES = [
        ('Assignments', 'Assignments'),
        ('Deadlines', 'Deadlines & Overdue'),
        ('Subjects', 'Subjects & Courses'),
        ('Account', 'Account & Security'),
        ('Errors', 'Errors & Troubleshooting'),
    ]

    question = models.CharField(max_length=300)
    answer = models.TextField()
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES, default='Assignments')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'

    def __str__(self):
        return f"[{self.category}] {self.question}"


class ErrorCode(models.Model):
    """HTTP & Site-specific error code catalog for AI assistant and user guide."""
    code = models.IntegerField(unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    common_causes = models.TextField(help_text="Typical reasons this error occurs.")
    solution = models.TextField(help_text="Recommended steps for students to resolve it.")
    is_custom = models.BooleanField(default=False, help_text="True if this is an Assignment Tracker custom error code.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class SupportTicket(models.Model):
    """Support ticket created when assistant cannot resolve an issue or upon user request."""
    STATUS_OPEN = 'open'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_RESOLVED = 'resolved'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_RESOLVED, 'Resolved'),
        (STATUS_CLOSED, 'Closed'),
    ]

    PRIORITY_LOW = 'low'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_HIGH = 'high'
    PRIORITY_URGENT = 'urgent'
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Low'),
        (PRIORITY_MEDIUM, 'Medium'),
        (PRIORITY_HIGH, 'High'),
        (PRIORITY_URGENT, 'Urgent'),
    ]

    ticket_number = models.CharField(max_length=32, unique=True)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='support_tickets')
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=100, default='General Support')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    source = models.CharField(max_length=50, default='assistant')  # 'assistant', 'error_page', 'form'
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ticket_number} - {self.subject} ({self.get_status_display()})"


class RequestLog(models.Model):
    """Request log entry for monitoring, analytics, and health check diagnostics."""
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=500)
    status_code = models.IntegerField()
    duration_ms = models.FloatField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True, default='')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['status_code']),
        ]

    def __str__(self):
        return f"{self.method} {self.path} -> {self.status_code} ({self.duration_ms:.1f}ms)"

