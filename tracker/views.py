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

from .models import Assignment, Subject
from .forms import (
    CustomUserCreationForm, CustomAuthenticationForm,
    AssignmentForm, SubjectForm
)


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
