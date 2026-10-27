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


class FAQAndErrorCodeTests(TestCase):
    def setUp(self):
        from django.core.management import call_command
        call_command('seed_demo')

    def test_minimum_10_faqs_in_sql(self):
        from .models import FAQ
        count = FAQ.objects.filter(is_active=True).count()
        self.assertGreaterEqual(count, 10, f"Expected at least 10 FAQs in SQL, found {count}")

    def test_minimum_8_error_codes(self):
        from .models import ErrorCode
        required_codes = {400, 401, 403, 404, 429, 500, 503, 488}
        existing_codes = set(ErrorCode.objects.values_list('code', flat=True))
        self.assertTrue(required_codes.issubset(existing_codes), f"Missing required error codes: {required_codes - existing_codes}")

    def test_custom_site_specific_error_code_exists(self):
        from .models import ErrorCode
        custom = ErrorCode.objects.filter(is_custom=True).first()
        self.assertIsNotNone(custom, "Site-specific custom error code not found")
        self.assertEqual(custom.code, 488)

    def test_faq_page_loads(self):
        resp = self.client.get(reverse('faq_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Frequently Asked Questions")
        self.assertContains(resp, "Ask Assistant about this")

    def test_error_code_page_loads(self):
        resp = self.client.get(reverse('error_code_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "404")
        self.assertContains(resp, "488")
        self.assertContains(resp, "Site-Specific Custom")


class CustomErrorPageTests(TestCase):
    def test_custom_404_view_rendered(self):
        resp = self.client.get('/this-path-does-not-exist-at-all-404/')
        self.assertEqual(resp.status_code, 404)
        self.assertContains(resp, "Page or Record Not Found", status_code=404)
        self.assertContains(resp, "Ask the Assistant", status_code=404)

    def test_custom_500_view_rendered(self):
        resp = self.client.get(reverse('test_500'))
        self.assertEqual(resp.status_code, 500)
        self.assertContains(resp, "Internal Server Error", status_code=500)
        self.assertContains(resp, "Ask the Assistant", status_code=500)


class AIAssistantAndTicketTests(TestCase):
    def setUp(self):
        from django.core.management import call_command
        call_command('seed_demo')

    def test_assistant_explains_error_404(self):
        resp = self.client.post(
            reverse('api_chat'),
            data='{"message": "What is error 404?"}',
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['matched_type'], 'error_code')
        self.assertIn('404', data['reply'])

    def test_assistant_explains_custom_error_488(self):
        resp = self.client.post(
            reverse('api_chat'),
            data='{"message": "Tell me about error 488"}',
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['matched_type'], 'error_code')
        self.assertIn('488', data['reply'])
        self.assertIn('Custom Site-Specific', data['reply'])

    def test_assistant_answers_from_sql_faq(self):
        resp = self.client.post(
            reverse('api_chat'),
            data='{"message": "How do I create a new assignment?"}',
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['matched_type'], 'faq')
        self.assertIn('Add Assignment', data['reply'])

    def test_assistant_suggests_ticket_when_unanswered(self):
        resp = self.client.post(
            reverse('api_chat'),
            data='{"message": "xyz completely unknown question about astrophysics rocket science"}',
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('can_create_ticket'))
        self.assertIn('support ticket', data['reply'].lower())

    def test_support_ticket_creation_in_sql(self):
        from .models import SupportTicket
        resp = self.client.post(
            reverse('api_ticket_create'),
            data='{"subject": "Cannot upload PDF", "description": "Submission fails on lab report", "email": "test@student.edu"}',
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'created')
        self.assertTrue(SupportTicket.objects.filter(ticket_number=data['ticket_number']).exists())


class HealthAndThirdPartyApiTests(TestCase):
    def test_health_check_html(self):
        resp = self.client.get(reverse('health_check'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "System Health & Service Diagnostics")
        self.assertContains(resp, "SQL Database")
        self.assertContains(resp, "MongoDB")
        self.assertContains(resp, "Third-Party Quote API")

    def test_health_check_json(self):
        resp = self.client.get(reverse('health_check') + '?format=json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('status', data)
        self.assertIn('checks', data)
        self.assertIn('database_sql', data['checks'])
        self.assertIn('mongodb', data['checks'])
        self.assertIn('third_party_api', data['checks'])

    def test_third_party_motivation_service_with_fallback(self):
        from .services import get_third_party_motivation
        result = get_third_party_motivation()
        self.assertIn('quote', result)
        self.assertIn('author', result)
        self.assertIn('latency_ms', result)
        self.assertTrue(result['latency_ms'] >= 0)

