# Assignment Tracker

A complete full-stack web application for college students to organize assignments, track deadlines, manage subjects, and monitor submission status.

Built with **Django 6**, **SQLite** (local), **PostgreSQL** (production), and a responsive vanilla CSS/JS frontend.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Nirmal61022/assignment-tracker)

**GitHub Repository:** [https://github.com/Nirmal61022/assignment-tracker](https://github.com/Nirmal61022/assignment-tracker)

---

## ✨ Features

- 📊 **Dashboard** with live statistics, Chart.js status distribution, due-soon list, upcoming deadlines
- 📝 **Assignment Management** — Create, read, update, delete with full CRUD
- 🔍 **Search, Filter & Sort** by subject, status, priority, and due date
- 🚨 **Automatic Overdue Detection** — computed in real-time, never stale
- ⚠️ **Due-Soon Alerts** — highlights assignments due within 48 hours
- ✅ **Mark as Submitted** — records exact submission timestamp
- 📖 **Subject Management** — color-coded subjects with assignment counts
- 📅 **Calendar / Deadlines View** — chronological upcoming and overdue lists
- 👤 **User Authentication** — registration, login, logout with full data isolation
- 📱 **Responsive Design** — works on desktop, tablet, and mobile
- 🔔 **Toast Notifications** for all actions
- 🔒 **Security** — CSRF protection, login required, per-user data isolation

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Python 3.10+
- pip

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd assignment_tracker

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your settings (defaults work for local dev)

# Run migrations
python manage.py migrate

# Seed demo data (optional)
python manage.py seed_demo
# Demo credentials: username=demo, password=demo123!

# Start the development server
python manage.py runserver
```

Then open: **http://127.0.0.1:8000**

---

## 🏗️ Project Structure

```
assignment_tracker/
├── manage.py
├── requirements.txt
├── Procfile              # For Render/Heroku deployment
├── .env.example          # Environment variable template
├── .gitignore
├── README.md
├── config/
│   ├── settings.py       # Django settings
│   ├── urls.py           # Root URL config
│   ├── wsgi.py
│   └── asgi.py
└── tracker/
    ├── models.py          # Subject, Assignment models
    ├── views.py           # All views (auth, CRUD, dashboard, etc.)
    ├── forms.py           # Form classes with validation
    ├── urls.py            # App URL patterns
    ├── admin.py           # Admin panel config
    ├── tests.py           # Automated test suite
    ├── migrations/        # Database migrations
    ├── templatetags/
    │   └── tracker_tags.py # Custom template filters/tags
    ├── management/
    │   └── commands/
    │       └── seed_demo.py # Demo data command
    ├── templates/tracker/ # All HTML templates
    │   ├── base.html
    │   ├── dashboard.html
    │   ├── assignment_list.html
    │   ├── assignment_detail.html
    │   ├── assignment_form.html
    │   ├── subject_list.html
    │   ├── calendar.html
    │   ├── login.html
    │   ├── register.html
    │   └── profile.html
    └── static/tracker/
        ├── css/style.css  # Complete responsive stylesheet
        └── js/app.js      # Toast, sidebar, charts, filters
```

---

## 🗄️ Models

### Subject
- `user` → ForeignKey(User)
- `name` → CharField (unique per user)
- `description` → TextField (optional)
- `color` → CharField (hex color)
- `created_at` → DateTimeField

### Assignment
- `user` → ForeignKey(User)
- `title` → CharField
- `subject` → ForeignKey(Subject)
- `description` → TextField
- `due_date` → DateField
- `due_time` → TimeField (optional)
- `priority` → low / medium / high
- `status` → pending / in_progress / submitted
- `submitted_at` → DateTimeField (auto-set on submission)
- `notes` → TextField
- `created_at`, `updated_at` → DateTimeField

**Computed properties** (not stored): `is_overdue`, `effective_status`, `due_soon`

---

## 🧪 Running Tests

```bash
python manage.py test tracker --verbosity=2
```

Tests cover:
- Authentication (register, login, logout, access control)
- Subject CRUD and delete-with-assignments guard
- Assignment CRUD, search, filter, mark-submitted
- Cross-user data isolation (returns 404)
- Model properties (is_overdue, due_soon)

---

## 🌐 Deployment (Render)

1. Push to GitHub
2. Create a new **Web Service** on [Render](https://render.com)
3. Set **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
4. Set **Start Command**: `gunicorn config.wsgi:application`
5. Add environment variables:
   - `SECRET_KEY` = (generate a random key)
   - `DEBUG` = `False`
   - `ALLOWED_HOSTS` = `your-app.onrender.com`
   - `DATABASE_URL` = (Render PostgreSQL connection string)
   - `CSRF_TRUSTED_ORIGINS` = `https://your-app.onrender.com`

### Generating a Secret Key
```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 🔐 Default Demo Credentials

After running `python manage.py seed_demo`:
- **Username:** `demo`
- **Password:** `demo123!`

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 6 |
| Database (local) | SQLite |
| Database (production) | PostgreSQL |
| Frontend | HTML5, CSS3, Vanilla JS |
| Charts | Chart.js 4 |
| Icons | Emoji (universal, no deps) |
| Static files | Whitenoise |
| WSGI server | Gunicorn |
| Config | python-decouple, dj-database-url |
