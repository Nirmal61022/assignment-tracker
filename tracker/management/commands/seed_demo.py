"""
Management command to seed demo data for testing.
Includes:
- Demo student user with assignments & subjects
- 12 comprehensive FAQs in SQL database
- 8 Error Codes (400, 401, 403, 404, 429, 500, 503, custom 488)
- Sample support tickets
Usage: python manage.py seed_demo
"""
import datetime
import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from tracker.models import Subject, Assignment, FAQ, ErrorCode, SupportTicket


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

FAQS = [
    (
        "How do I create a new assignment?",
        "Click the '+ Add Assignment' button in the navigation bar or dashboard. Fill in the required fields: Title, Subject, Due Date, Priority (Low, Medium, High), and optional description/notes, then click Save.",
        "Assignments", 1
    ),
    (
        "How are overdue assignments calculated?",
        "Assignments are determined to be overdue dynamically based on your current local time and the assigned due date and time. An assignment is overdue if the deadline has passed and the status has not been changed to 'Submitted'. Overdue status is computed dynamically in real-time.",
        "Deadlines", 2
    ),
    (
        "What does the 'Due Soon' indicator mean?",
        "The 'Due Soon' badge and amber warning highlight any pending or in-progress assignment that is due within the next 48 hours, helping you prioritize urgent submissions.",
        "Deadlines", 3
    ),
    (
        "How do I mark an assignment as submitted?",
        "You can mark an assignment as submitted by clicking the 'Mark Submitted' or '✅ Submit' button on the assignment card, detail page, or upcoming calendar view. The system automatically records the exact submission timestamp.",
        "Assignments", 4
    ),
    (
        "Can I edit an assignment after creating it?",
        "Yes! Navigate to the assignment detail page or click the edit icon (✏️) on the assignment card. You can change the title, deadline, priority, status, subject, and notes at any time.",
        "Assignments", 5
    ),
    (
        "How do I manage subjects or courses?",
        "Go to the 'Subjects' tab in the sidebar. You can create new subjects with distinct color badges, rename existing ones, or view assignment counts per subject. Deleting a subject that still has active assignments is blocked to prevent orphaned records.",
        "Subjects", 6
    ),
    (
        "Is my assignment data private from other students?",
        "Yes, absolutely. The system strictly isolates student data using Django's built-in session authentication and ownership validation. You can only view, edit, or delete subjects and assignments tied to your account.",
        "Account", 7
    ),
    (
        "How does the calendar and upcoming deadlines view work?",
        "The Calendar page arranges your workload chronologically into two sections: Overdue Assignments that need immediate attention and Upcoming Deadlines sorted by urgency, showing exact days and hours remaining.",
        "Deadlines", 8
    ),
    (
        "What should I do if I encounter an error code like 404 or 500?",
        "You can ask our integrated AI Assistant in the bottom right corner! Mention the error code (e.g. 'Explain error 404') and it will break down the cause and resolution steps. You can also view the full error code directory on the Error Codes page.",
        "Errors", 9
    ),
    (
        "How do I open a support ticket if something goes wrong?",
        "If you experience a system bug or need human assistance, open the AI Assistant widget and click 'Create Support Ticket' or ask 'I need support'. Fill in your issue description, and a ticket will be saved to our database with a unique tracking ID.",
        "Errors", 10
    ),
    (
        "Can I filter and search assignments?",
        "Yes. On the 'All Assignments' page, use the search bar to find assignments by keyword in title/description, or use the dropdown filters to sort by subject, priority (High/Medium/Low), or status (Pending/In Progress/Submitted).",
        "Assignments", 11
    ),
    (
        "What technologies power this Assignment Tracker?",
        "Assignment Tracker is built with Python Django 6 on the backend, SQLite for local development, PostgreSQL for production hosting, WhiteNoise for static asset delivery, and MongoDB for assistant chat logs and feedback.",
        "Account", 12
    ),
]

ERROR_CODES = [
    (
        400, "Bad Request",
        "The server cannot process the request due to malformed request syntax, invalid parameters, or missing required form fields.",
        "Submitting an assignment without a title or date, corrupt form encoding, or invalid date formats.",
        "Verify all required form fields marked with an asterisk (*) are filled in and format dates as YYYY-MM-DD.",
        False
    ),
    (
        401, "Unauthorized",
        "Authentication is required and has failed or has not yet been provided.",
        "User session expired, cookies cleared, or attempting to view protected pages before logging in.",
        "Log in with your registered username and password. If your session expired, sign in again to refresh your authentication cookie.",
        False
    ),
    (
        403, "Forbidden",
        "The server understood the request, but refuses to authorize it because you do not have permission to access the requested resource.",
        "Attempting to view, edit, or delete an assignment or subject owned by another student.",
        "Ensure you are logged into your own account. You can only modify records created under your user profile.",
        False
    ),
    (
        404, "Not Found",
        "The requested URL or database record does not exist on the server.",
        "Mistyped URL path, navigating to an assignment ID that was recently deleted, or outdated bookmarks.",
        "Check the URL spelling, click 'Ask the assistant' for suggestions, or return to your Dashboard.",
        False
    ),
    (
        429, "Too Many Requests",
        "The user has sent too many requests in a given amount of time (rate limiting).",
        "Rapidly submitting forms, spamming chat assistant messages, or repeated failed login attempts.",
        "Wait 30-60 seconds before trying again. For AI assistant queries, allow responses to complete before sending new questions.",
        False
    ),
    (
        500, "Internal Server Error",
        "The server encountered an unexpected condition that prevented it from fulfilling the request.",
        "Unhandled backend exception, template rendering error, or internal database query failure.",
        "Reload the page. If the issue persists, click 'Ask the assistant' to create an automated support ticket for the developers.",
        False
    ),
    (
        503, "Service Unavailable",
        "The server is currently unable to handle the request due to a temporary overloading or maintenance of the server.",
        "Scheduled database maintenance, server reboot during deployment, or upstream connectivity drop.",
        "Wait 1-2 minutes and refresh the page. Check the /health/ diagnostics page for live system status.",
        False
    ),
    (
        488, "Assignment Submission Locked",
        "Custom Site-Specific Error: Indicates that the submission window has officially closed and submissions are locked by course policy.",
        "Attempting to submit or edit an assignment whose strict deadline has elapsed and instructor policy disallows late submissions.",
        "Contact your course instructor or department coordinator to request a submission deadline extension, or submit a support ticket.",
        True
    ),
]


class Command(BaseCommand):
    help = 'Seed demo data for testing, including FAQs, Error Codes, and Support Tickets'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='demo', help='Demo username')
        parser.add_argument('--password', default='demo123!', help='Demo password')
        parser.add_argument('--email', default='demo@example.com', help='Demo email')

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        email = options['email']

        # 1. Create or get user
        user, created = User.objects.get_or_create(username=username, defaults={'email': email})
        if created:
            user.set_password(password)
            user.first_name = 'Demo'
            user.last_name = 'Student'
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created user: {username}'))
        else:
            self.stdout.write(f'Using existing user: {username}')

        # 2. Create subjects
        subject_map = {}
        for name, color in SUBJECTS:
            subj, _ = Subject.objects.get_or_create(
                user=user, name=name,
                defaults={'color': color}
            )
            subject_map[name] = subj

        # 3. Create assignments
        today = timezone.localdate()
        created_count = 0

        for title, subj_name, desc, priority, days_offset in ASSIGNMENTS:
            due_date = today + datetime.timedelta(days=days_offset)
            subject = subject_map[subj_name]

            if days_offset < -1:
                status = 'submitted' if random.random() > 0.5 else 'pending'
            elif days_offset < 0:
                status = 'pending'
            else:
                status = random.choice(['pending', 'in_progress', 'pending'])

            submitted_at = None
            if status == 'submitted':
                submitted_at = timezone.now() - datetime.timedelta(days=random.randint(1, 3))

            _, created_flag = Assignment.objects.get_or_create(
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

        # 4. Seed FAQs
        faq_count = 0
        for q, a, cat, order in FAQS:
            _, created_faq = FAQ.objects.get_or_create(
                question=q,
                defaults={
                    'answer': a,
                    'category': cat,
                    'order': order,
                    'is_active': True,
                }
            )
            if created_faq:
                faq_count += 1

        # 5. Seed Error Codes
        err_count = 0
        for code, name, desc, causes, sol, is_custom in ERROR_CODES:
            _, created_err = ErrorCode.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'description': desc,
                    'common_causes': causes,
                    'solution': sol,
                    'is_custom': is_custom,
                }
            )
            if created_err:
                err_count += 1

        # 6. Seed Sample Support Ticket
        SupportTicket.objects.get_or_create(
            ticket_number="TICK-2026-DEMO01",
            defaults={
                'user': user,
                'email': user.email,
                'subject': "Assistance with Linear Algebra Assignment Submission",
                'description': "I need clarification on submission formatting for problem set 3.",
                'category': "Assignments",
                'status': "resolved",
                'priority': "medium",
                'source': "assistant",
            }
        )

        self.stdout.write(self.style.SUCCESS(
            f'Demo data successfully seeded:\n'
            f'- {created_count} assignments created/checked\n'
            f'- {len(FAQS)} FAQs seeded in SQL database\n'
            f'- {len(ERROR_CODES)} Error Codes seeded in SQL database (7 HTTP + 1 Custom 488)\n'
            f'- Login credentials: username={username}, password={password}'
        ))
