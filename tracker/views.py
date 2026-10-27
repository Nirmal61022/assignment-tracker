"""
Views for Assignment Tracker app.
"""
import json
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.db.models import Q, Count
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST

from .models import Assignment, Subject, FAQ, ErrorCode, SupportTicket, RequestLog
from .forms import (
    CustomUserCreationForm, CustomAuthenticationForm,
    AssignmentForm, SubjectForm
)
from .services import get_third_party_motivation, check_third_party_api_health, process_assistant_message
from .mongo import log_chat_message, save_feedback, check_mongo_connection


# ─────────────────────────── Auth Views ──────────────────────────────

def index(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.username}! Your account has been created.')
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'tracker/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get('next', 'dashboard')
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect(next_url)
    else:
        form = CustomAuthenticationForm()
    return render(request, 'tracker/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


@login_required
def profile_view(request):
    user = request.user
    assignments = Assignment.objects.filter(user=user)
    total = assignments.count()
    submitted = assignments.filter(status='submitted').count()
    subjects_count = Subject.objects.filter(user=user).count()
    context = {
        'total_assignments': total,
        'submitted': submitted,
        'subjects_count': subjects_count,
        'member_since': user.date_joined,
    }
    return render(request, 'tracker/profile.html', context)


# ─────────────────────────── Dashboard ───────────────────────────────

@login_required
def dashboard(request):
    user = request.user
    now = timezone.now()
    today = timezone.localdate()
    soon_threshold = now + datetime.timedelta(hours=48)

    all_assignments = Assignment.objects.filter(user=user).select_related('subject')

    # Compute counts
    total = all_assignments.count()
    submitted = all_assignments.filter(status='submitted').count()
    in_progress = all_assignments.filter(status='in_progress').count()

    # Overdue: not submitted and past due
    overdue_list = []
    pending_list = []
    due_soon_list = []
    upcoming_list = []

    for a in all_assignments:
        if a.status == 'submitted':
            continue
        if a.is_overdue:
            overdue_list.append(a)
        elif a.due_soon:
            due_soon_list.append(a)
        else:
            pending_list.append(a)

    overdue_count = len(overdue_list)
    pending_count = len(pending_list) + in_progress

    # Upcoming (next 7 days, not overdue/submitted)
    upcoming_list = (
        all_assignments
        .exclude(status='submitted')
        .filter(due_date__gte=today, due_date__lte=today + datetime.timedelta(days=7))
        .order_by('due_date', 'due_time')[:5]
    )

    # Recent 5 assignments
    recent = all_assignments.order_by('-created_at')[:5]

    # Chart data: status distribution
    chart_data = {
        'labels': ['Pending', 'In Progress', 'Submitted', 'Overdue'],
        'data': [len(pending_list), in_progress, submitted, overdue_count],
        'colors': ['#6366f1', '#f59e0b', '#10b981', '#ef4444'],
    }

    # Third-party motivation quote with timeout & fallback
    motivation = get_third_party_motivation()

    context = {
        'total': total,
        'pending_count': pending_count,
        'submitted': submitted,
        'overdue_count': overdue_count,
        'due_soon': due_soon_list[:5],
        'upcoming': upcoming_list,
        'recent': recent,
        'chart_data': json.dumps(chart_data),
        'has_assignments': total > 0,
        'motivation': motivation,
    }
    return render(request, 'tracker/dashboard.html', context)


# ─────────────────────── Assignment Views ────────────────────────────

@login_required
def assignment_list(request):
    user = request.user
    queryset = Assignment.objects.filter(user=user).select_related('subject')

    # Search
    search = request.GET.get('q', '').strip()
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )

    # Filter by subject
    subject_id = request.GET.get('subject', '')
    if subject_id:
        queryset = queryset.filter(subject_id=subject_id)

    # Filter by priority
    priority = request.GET.get('priority', '')
    if priority:
        queryset = queryset.filter(priority=priority)

    # Filter by status (including virtual 'overdue')
    status_filter = request.GET.get('status', '')
    if status_filter == 'overdue':
        # Overdue: not submitted, past due date
        today = timezone.localdate()
        queryset = queryset.exclude(status='submitted').filter(due_date__lt=today)
    elif status_filter:
        queryset = queryset.filter(status=status_filter)

    # Sorting
    sort = request.GET.get('sort', 'due_date')
    valid_sorts = {
        'due_date': 'due_date',
        '-due_date': '-due_date',
        'title': 'title',
        '-title': '-title',
        'priority': 'priority',
        'created': '-created_at',
    }
    order_field = valid_sorts.get(sort, 'due_date')
    queryset = queryset.order_by(order_field)

    # Pagination
    paginator = Paginator(queryset, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    subjects = Subject.objects.filter(user=user)
    context = {
        'page_obj': page_obj,
        'subjects': subjects,
        'search': search,
        'selected_subject': subject_id,
        'selected_priority': priority,
        'selected_status': status_filter,
        'current_sort': sort,
        'total_count': queryset.count(),
    }
    return render(request, 'tracker/assignment_list.html', context)


@login_required
def assignment_detail(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk, user=request.user)
    return render(request, 'tracker/assignment_detail.html', {'assignment': assignment})


@login_required
def assignment_create(request):
    if request.method == 'POST':
        form = AssignmentForm(request.POST, user=request.user)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.user = request.user
            # Handle submitted_at
            if assignment.status == 'submitted' and not assignment.submitted_at:
                assignment.submitted_at = timezone.now()
            assignment.save()
            messages.success(request, f'Assignment "{assignment.title}" created successfully!')
            return redirect('assignment_list')
    else:
        form = AssignmentForm(user=request.user)

    subjects = Subject.objects.filter(user=request.user)
    context = {'form': form, 'subjects': subjects, 'action': 'Create'}
    return render(request, 'tracker/assignment_form.html', context)


@login_required
def assignment_edit(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk, user=request.user)
    if request.method == 'POST':
        form = AssignmentForm(request.POST, instance=assignment, user=request.user)
        if form.is_valid():
            assignment = form.save(commit=False)
            # Handle submitted_at
            if assignment.status == 'submitted' and not assignment.submitted_at:
                assignment.submitted_at = timezone.now()
            elif assignment.status != 'submitted':
                assignment.submitted_at = None
            assignment.save()
            messages.success(request, f'Assignment "{assignment.title}" updated successfully!')
            return redirect('assignment_detail', pk=assignment.pk)
    else:
        form = AssignmentForm(instance=assignment, user=request.user)

    context = {'form': form, 'assignment': assignment, 'action': 'Edit'}
    return render(request, 'tracker/assignment_form.html', context)


@login_required
@require_POST
def assignment_delete(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk, user=request.user)
    title = assignment.title
    assignment.delete()
    messages.success(request, f'Assignment "{title}" deleted.')
    return redirect('assignment_list')


@login_required
@require_POST
def assignment_mark_submitted(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk, user=request.user)
    assignment.mark_submitted()
    messages.success(request, f'"{assignment.title}" marked as submitted!')
    next_url = request.POST.get('next', request.META.get('HTTP_REFERER', 'dashboard'))
    return redirect(next_url)


# ─────────────────────────── Subject Views ───────────────────────────

@login_required
def subject_list(request):
    subjects = Subject.objects.filter(user=request.user).annotate(
        total_assignments=Count('assignments'),
    )
    form = SubjectForm(user=request.user)
    context = {'subjects': subjects, 'form': form}
    return render(request, 'tracker/subject_list.html', context)


@login_required
def subject_create(request):
    if request.method == 'POST':
        form = SubjectForm(request.POST, user=request.user)
        if form.is_valid():
            subject = form.save(commit=False)
            subject.user = request.user
            subject.save()
            messages.success(request, f'Subject "{subject.name}" created!')
            return redirect('subject_list')
        else:
            # Re-render with errors
            subjects = Subject.objects.filter(user=request.user).annotate(
                total_assignments=Count('assignments'),
            )
            context = {'subjects': subjects, 'form': form}
            return render(request, 'tracker/subject_list.html', context)
    return redirect('subject_list')


@login_required
def subject_edit(request, pk):
    subject = get_object_or_404(Subject, pk=pk, user=request.user)
    if request.method == 'POST':
        form = SubjectForm(request.POST, instance=subject, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Subject "{subject.name}" updated!')
            return redirect('subject_list')
    else:
        form = SubjectForm(instance=subject, user=request.user)

    subjects = Subject.objects.filter(user=request.user).annotate(
        total_assignments=Count('assignments'),
    )
    context = {'subjects': subjects, 'form': form, 'edit_subject': subject}
    return render(request, 'tracker/subject_list.html', context)


@login_required
@require_POST
def subject_delete(request, pk):
    subject = get_object_or_404(Subject, pk=pk, user=request.user)
    if subject.assignments.exists():
        messages.error(
            request,
            f'Cannot delete "{subject.name}" — it has {subject.assignments.count()} assignment(s). '
            'Reassign or delete those assignments first.'
        )
    else:
        name = subject.name
        subject.delete()
        messages.success(request, f'Subject "{name}" deleted.')
    return redirect('subject_list')


# ─────────────────────────── Calendar View ───────────────────────────

@login_required
def calendar_view(request):
    user = request.user
    today = timezone.localdate()

    assignments = (
        Assignment.objects
        .filter(user=user)
        .exclude(status='submitted')
        .select_related('subject')
        .order_by('due_date', 'due_time')
    )

    # Group by date for the calendar
    upcoming = assignments.filter(due_date__gte=today).order_by('due_date')[:30]
    overdue = assignments.filter(due_date__lt=today).order_by('-due_date')[:10]

    context = {
        'upcoming': upcoming,
        'overdue': overdue,
        'today': today,
    }
    return render(request, 'tracker/calendar.html', context)


# ─────────────────────── FAQ & Error Code Views ───────────────────────

def faq_list(request):
    """Display at least 10 FAQs stored in the SQL database, grouped and searchable."""
    category = request.GET.get('category', '').strip()
    search = request.GET.get('q', '').strip()

    faqs = FAQ.objects.filter(is_active=True).order_by('order', 'id')

    if category:
        faqs = faqs.filter(category=category)
    if search:
        faqs = faqs.filter(Q(question__icontains=search) | Q(answer__icontains=search))

    categories = FAQ.objects.filter(is_active=True).values_list('category', flat=True).distinct()

    context = {
        'faqs': faqs,
        'categories': categories,
        'selected_category': category,
        'search': search,
        'total_count': faqs.count(),
    }
    return render(request, 'tracker/faq_list.html', context)


def error_code_list(request):
    """Display at least 8 error codes (7 HTTP + 1 site-specific) with explanations and solutions."""
    search = request.GET.get('q', '').strip()
    error_codes = ErrorCode.objects.all().order_by('code')

    if search:
        error_codes = error_codes.filter(
            Q(code__icontains=search) |
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )

    context = {
        'error_codes': error_codes,
        'search': search,
        'total_count': error_codes.count(),
    }
    return render(request, 'tracker/error_code_list.html', context)


# ─────────────────────── Health Check & Diagnostics ───────────────────

def health_check(request):
    """
    Health check endpoint: verifies SQL Database, MongoDB, and Third-Party API status.
    Returns JSON if requested, otherwise renders rich diagnostics dashboard.
    """
    import time
    from django.db import connection

    start_time = time.time()
    checks = {}

    # 1. SQL Database Check
    try:
        sql_start = time.time()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        sql_latency = round((time.time() - sql_start) * 1000, 2)
        checks['database_sql'] = {
            'status': 'healthy',
            'engine': connection.vendor,
            'latency_ms': sql_latency,
            'assignments_count': Assignment.objects.count(),
            'faqs_count': FAQ.objects.count(),
            'error_codes_count': ErrorCode.objects.count(),
            'tickets_count': SupportTicket.objects.count(),
        }
    except Exception as e:
        checks['database_sql'] = {
            'status': 'unhealthy',
            'error': str(e)
        }

    # 2. MongoDB Check
    checks['mongodb'] = check_mongo_connection()

    # 3. Third-party Quote API Check
    checks['third_party_api'] = check_third_party_api_health()

    # 4. Request Logs
    recent_logs = RequestLog.objects.order_by('-timestamp')[:15]

    overall_status = 'healthy'
    if checks['database_sql']['status'] != 'healthy':
        overall_status = 'unhealthy'
    elif checks['mongodb'].get('status') == 'degraded':
        overall_status = 'degraded'

    total_duration_ms = round((time.time() - start_time) * 1000, 2)

    data = {
        'status': overall_status,
        'timestamp': timezone.now().isoformat(),
        'duration_ms': total_duration_ms,
        'checks': checks,
    }

    if request.GET.get('format') == 'json' or request.headers.get('Accept') == 'application/json':
        status_code = 200 if overall_status in ['healthy', 'degraded'] else 503
        return JsonResponse(data, status=status_code)

    return render(request, 'tracker/health.html', {
        'status': overall_status,
        'data': data,
        'recent_logs': recent_logs,
    })


# ─────────────────────── AI Assistant APIs ────────────────────────────

@require_POST
def api_chat(request):
    """
    AI Assistant chat endpoint.
    Retrieves answers from SQL FAQs and Error Codes, suggests tickets on unknown queries,
    and logs conversation to MongoDB.
    """
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        payload = request.POST

    user_message = payload.get('message', '').strip()
    session_id = payload.get('session_id', 'anonymous_session')
    context_code = payload.get('context_code')

    if not user_message:
        return JsonResponse({'error': 'Message cannot be empty.'}, status=400)

    # Process query via intelligence engine
    result = process_assistant_message(
        user_message=user_message,
        user=request.user if request.user.is_authenticated else None,
        context_code=context_code
    )

    # Log to MongoDB (with fallback)
    username = request.user.username if request.user.is_authenticated else 'Anonymous'
    user_id = request.user.id if request.user.is_authenticated else None

    logged_to_mongo, log_id = log_chat_message(
        session_id=session_id,
        user_id=user_id,
        username=username,
        user_message=user_message,
        assistant_response=result['reply'],
        metadata={
            'matched_type': result['matched_type'],
            'matched_id': result.get('matched_id'),
            'can_create_ticket': result.get('can_create_ticket', False),
            'ip': request.META.get('REMOTE_ADDR'),
        }
    )

    result['session_id'] = session_id
    result['message_id'] = log_id
    result['logged_to_mongo'] = logged_to_mongo

    return JsonResponse(result)


@require_POST
def api_ticket_create(request):
    """
    Create a support ticket stored in SQL database.
    Can be invoked by the AI Assistant or via the web form.
    """
    import uuid

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        payload = request.POST

    subject = payload.get('subject', '').strip()
    description = payload.get('description', '').strip()
    email = payload.get('email', '').strip()
    category = payload.get('category', 'General Support').strip()
    priority = payload.get('priority', 'medium').strip()
    source = payload.get('source', 'assistant').strip()

    if not subject:
        subject = "Assistant Support Request"
    if not description:
        return JsonResponse({'error': 'Description is required to create a support ticket.'}, status=400)

    # Auto-fill email if user is logged in
    if not email and request.user.is_authenticated and request.user.email:
        email = request.user.email
    elif not email:
        email = 'student@example.com'

    # Generate unique ticket number
    ticket_num = f"TICK-{timezone.now().year}-{uuid.uuid4().hex[:6].upper()}"

    ticket = SupportTicket.objects.create(
        ticket_number=ticket_num,
        user=request.user if request.user.is_authenticated else None,
        email=email,
        subject=subject,
        description=description,
        category=category,
        priority=priority if priority in ['low', 'medium', 'high', 'urgent'] else 'medium',
        source=source,
    )

    return JsonResponse({
        'status': 'created',
        'ticket_number': ticket.ticket_number,
        'ticket_id': ticket.id,
        'message': f"Support ticket #{ticket.ticket_number} created successfully in SQL database. Our team will review it shortly.",
    })


def ticket_list(request):
    """List support tickets for logged-in user or allow creating new tickets."""
    if request.user.is_authenticated:
        tickets = SupportTicket.objects.filter(user=request.user)
    else:
        tickets = SupportTicket.objects.none()

    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', 'General Support')
        priority = request.POST.get('priority', 'medium')
        email = request.POST.get('email', '').strip()

        if not email and request.user.is_authenticated:
            email = request.user.email or 'student@example.com'

        if subject and description:
            import uuid
            ticket_num = f"TICK-{timezone.now().year}-{uuid.uuid4().hex[:6].upper()}"
            ticket = SupportTicket.objects.create(
                ticket_number=ticket_num,
                user=request.user if request.user.is_authenticated else None,
                email=email,
                subject=subject,
                description=description,
                category=category,
                priority=priority,
                source='web_form',
            )
            messages.success(request, f"Support ticket #{ticket.ticket_number} created successfully!")
            return redirect('ticket_list')
        else:
            messages.error(request, "Subject and description are required.")

    return render(request, 'tracker/ticket_list.html', {'tickets': tickets})


@require_POST
def api_feedback(request):
    """Save assistant feedback (thumbs up/down) to MongoDB."""
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        payload = request.POST

    session_id = payload.get('session_id', 'unknown')
    message_id = payload.get('message_id', '')
    rating = payload.get('rating', 'up')
    comment = payload.get('comment', '').strip()
    user_id = request.user.id if request.user.is_authenticated else None

    logged_to_mongo, feedback_id = save_feedback(
        session_id=session_id,
        message_id=message_id,
        rating=rating,
        comment=comment,
        user_id=user_id,
    )

    return JsonResponse({
        'status': 'success',
        'feedback_id': feedback_id,
        'logged_to_mongo': logged_to_mongo,
    })


def api_motivation(request):
    """Endpoint for third-party motivation API with timeout and fallback."""
    data = get_third_party_motivation()
    return JsonResponse(data)


# ─────────────────────── Custom Error Handlers & Tests ───────────────

def custom_404_view(request, exception=None):
    """Custom 404 page with integrated 'Ask the assistant' option."""
    return render(request, '404.html', {'status_code': 404, 'path': request.path}, status=404)


def custom_500_view(request):
    """Custom 500 page with integrated 'Ask the assistant' option."""
    return render(request, '500.html', {'status_code': 500}, status=500)


def test_404_view(request):
    """Test endpoint to demonstrate the custom 404 page."""
    raise Http404("This is a demonstration 404 error page.")


def test_500_view(request):
    """Test endpoint to demonstrate the custom 500 page."""
    return custom_500_view(request)

