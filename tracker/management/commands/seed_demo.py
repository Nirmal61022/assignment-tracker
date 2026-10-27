"""
Management command to seed demo data for testing.
Usage: python manage.py seed_demo --username demo --password demo123
"""
import datetime
import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from tracker.models import Subject, Assignment


SUBJECTS = [
    ('Mathematics', '#6366f1'),
    ('Physics', '#8b5cf6'),
    ('Computer Science', '#06b6d4'),
    ('English Literature', '#10b981'),
    ('History', '#f59e0b'),
    ('Chemistry', '#ef4444'),
]

ASSIGNMENTS = [
    ('Calculus Problem Set 3', 'Mathematics', 'Solve problems 1-20 from Chapter 5.', 'high', 2),
    ('Newton\'s Laws Lab Report', 'Physics', 'Write up the lab experiment on Newton\'s laws.', 'high', -1),
    ('Python OOP Assignment', 'Computer Science', 'Implement a class hierarchy for a library system.', 'medium', 5),
    ('Essay: Hamlet Analysis', 'English Literature', 'Analyze the themes of revenge and mortality in Hamlet.', 'high', 7),
    ('WWI Causes Research Paper', 'History', '2000-word research paper on the causes of WWI.', 'medium', -3),
    ('Organic Chemistry Quiz Prep', 'Chemistry', 'Review chapters 8-10 for the upcoming quiz.', 'low', 1),
    ('Linear Algebra Midterm Review', 'Mathematics', 'Review all topics covered so far this semester.', 'high', 3),
    ('Quantum Mechanics Problem Set', 'Physics', 'Problems on wave-particle duality.', 'medium', 10),
    ('Database Design Project', 'Computer Science', 'Design an ER diagram and schema for a hospital system.', 'high', 14),
    ('Poetry Analysis', 'English Literature', 'Analyze three poems of your choice.', 'low', -5),
    ('Industrial Revolution Essay', 'History', 'Discuss the impact of the industrial revolution.', 'medium', 21),
    ('Titration Lab', 'Chemistry', 'Conduct acid-base titration and report results.', 'high', -2),
]


class Command(BaseCommand):
    help = 'Seed demo data for testing'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='demo', help='Demo username')
        parser.add_argument('--password', default='demo123!', help='Demo password')
        parser.add_argument('--email', default='demo@example.com', help='Demo email')

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        email = options['email']

        # Create or get user
        user, created = User.objects.get_or_create(username=username, defaults={'email': email})
        if created:
            user.set_password(password)
            user.first_name = 'Demo'
            user.last_name = 'Student'
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created user: {username}'))
        else:
            self.stdout.write(f'Using existing user: {username}')

        # Create subjects
        subject_map = {}
        for name, color in SUBJECTS:
            subj, _ = Subject.objects.get_or_create(
                user=user, name=name,
                defaults={'color': color}
            )
            subject_map[name] = subj

        today = timezone.localdate()
        created_count = 0

        for title, subj_name, desc, priority, days_offset in ASSIGNMENTS:
            due_date = today + datetime.timedelta(days=days_offset)
            subject = subject_map[subj_name]

            # Determine status
            if days_offset < -1:
                status = 'submitted' if random.random() > 0.5 else 'pending'
            elif days_offset < 0:
                status = 'pending'
            else:
                status = random.choice(['pending', 'in_progress', 'pending'])

            submitted_at = None
            if status == 'submitted':
                submitted_at = timezone.now() - datetime.timedelta(days=random.randint(1, 3))

            assignment, created_flag = Assignment.objects.get_or_create(
                user=user, title=title,
                defaults={
                    'subject': subject,
                    'description': desc,
                    'due_date': due_date,
                    'due_time': datetime.time(23, 59),
                    'priority': priority,
                    'status': status,
                    'submitted_at': submitted_at,
                }
            )
            if created_flag:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Demo data seeded: {created_count} assignments created.\n'
            f'Login: username={username}, password={password}'
        ))
