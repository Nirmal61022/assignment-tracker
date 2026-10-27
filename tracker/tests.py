"""
Tests for Assignment Tracker app.
"""
import datetime
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from .models import Subject, Assignment


class AuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123', email='test@test.com'
        )

    def test_register_page_loads(self):
        resp = self.client.get(reverse('register'))
        self.assertEqual(resp.status_code, 200)

    def test_register_creates_user(self):
        resp = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'new@test.com',
            'password1': 'complexpass123!',
            'password2': 'complexpass123!',
        })
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_login_page_loads(self):
        resp = self.client.get(reverse('login'))
        self.assertEqual(resp.status_code, 200)

    def test_login_success(self):
        resp = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'testpass123',
        })
        self.assertRedirects(resp, reverse('dashboard'))

    def test_logout(self):
        self.client.login(username='testuser', password='testpass123')
        resp = self.client.get(reverse('logout'))
        self.assertRedirects(resp, reverse('login'))

    def test_dashboard_requires_login(self):
        resp = self.client.get(reverse('dashboard'))
        self.assertRedirects(resp, f'/login/?next=/dashboard/')


class SubjectTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')

    def test_create_subject(self):
        resp = self.client.post(reverse('subject_create'), {'name': 'Math', 'color': '#6366f1'})
        self.assertTrue(Subject.objects.filter(user=self.user, name='Math').exists())

    def test_subject_list(self):
        Subject.objects.create(user=self.user, name='Physics')
        resp = self.client.get(reverse('subject_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Physics')

    def test_delete_subject_with_assignments_blocked(self):
        subj = Subject.objects.create(user=self.user, name='Physics')
        Assignment.objects.create(
            user=self.user, title='Test', subject=subj,
            due_date=datetime.date.today() + datetime.timedelta(days=1),
            priority='medium', status='pending',
        )
        resp = self.client.post(reverse('subject_delete', args=[subj.pk]))
        self.assertTrue(Subject.objects.filter(pk=subj.pk).exists())  # Not deleted

    def test_delete_subject_no_assignments(self):
        subj = Subject.objects.create(user=self.user, name='Empty Subject')
        resp = self.client.post(reverse('subject_delete', args=[subj.pk]))
        self.assertFalse(Subject.objects.filter(pk=subj.pk).exists())


class AssignmentTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.other_user = User.objects.create_user(username='otheruser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        self.subject = Subject.objects.create(user=self.user, name='Math')
        self.tomorrow = datetime.date.today() + datetime.timedelta(days=1)

    def _create_assignment(self, **kwargs):
        defaults = {
            'user': self.user, 'title': 'Test Assignment',
            'subject': self.subject, 'due_date': self.tomorrow,
            'priority': 'medium', 'status': 'pending',
        }
        defaults.update(kwargs)
        return Assignment.objects.create(**defaults)

    def test_create_assignment(self):
        resp = self.client.post(reverse('assignment_create'), {
            'title': 'New Assignment',
            'subject': self.subject.pk,
            'due_date': self.tomorrow.isoformat(),
            'priority': 'high',
            'status': 'pending',
        })
        self.assertTrue(Assignment.objects.filter(user=self.user, title='New Assignment').exists())

    def test_assignment_list(self):
        self._create_assignment()
        resp = self.client.get(reverse('assignment_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Test Assignment')

    def test_assignment_detail(self):
        a = self._create_assignment()
        resp = self.client.get(reverse('assignment_detail', args=[a.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_assignment_edit(self):
        a = self._create_assignment()
        resp = self.client.post(reverse('assignment_edit', args=[a.pk]), {
            'title': 'Updated Title',
            'subject': self.subject.pk,
            'due_date': self.tomorrow.isoformat(),
            'priority': 'low',
            'status': 'in_progress',
        })
        a.refresh_from_db()
        self.assertEqual(a.title, 'Updated Title')

    def test_assignment_delete(self):
        a = self._create_assignment()
        resp = self.client.post(reverse('assignment_delete', args=[a.pk]))
        self.assertFalse(Assignment.objects.filter(pk=a.pk).exists())

    def test_mark_submitted(self):
        a = self._create_assignment()
        resp = self.client.post(reverse('assignment_submit', args=[a.pk]), {'next': '/'})
        a.refresh_from_db()
        self.assertEqual(a.status, 'submitted')
        self.assertIsNotNone(a.submitted_at)

    def test_cannot_access_other_users_assignment(self):
        other_subj = Subject.objects.create(user=self.other_user, name='Other Math')
        other_assignment = Assignment.objects.create(
            user=self.other_user, title='Other Assignment',
            subject=other_subj, due_date=self.tomorrow,
            priority='medium', status='pending',
        )
        resp = self.client.get(reverse('assignment_detail', args=[other_assignment.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_search_filter(self):
        self._create_assignment(title='Algebra Homework')
        self._create_assignment(title='Physics Lab')
        resp = self.client.get(reverse('assignment_list') + '?q=algebra')
        self.assertContains(resp, 'Algebra Homework')
        self.assertNotContains(resp, 'Physics Lab')

    def test_is_overdue_property(self):
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        a = self._create_assignment(due_date=yesterday)
        self.assertTrue(a.is_overdue)

    def test_is_not_overdue_when_submitted(self):
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        a = self._create_assignment(due_date=yesterday, status='submitted',
                                     submitted_at=timezone.now())
        self.assertFalse(a.is_overdue)


class ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.subject = Subject.objects.create(user=self.user, name='Math')

    def test_subject_str(self):
        self.assertEqual(str(self.subject), 'Math')

    def test_assignment_str(self):
        a = Assignment.objects.create(
            user=self.user, title='Test', subject=self.subject,
            due_date=datetime.date.today() + datetime.timedelta(days=1),
            priority='medium', status='pending',
        )
        self.assertIn('Test', str(a))

    def test_due_soon_within_48h(self):
        soon = datetime.date.today() + datetime.timedelta(days=1)
        a = Assignment.objects.create(
            user=self.user, title='Soon', subject=self.subject,
            due_date=soon, priority='medium', status='pending',
        )
        self.assertTrue(a.due_soon)
