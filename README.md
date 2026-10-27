# Assignment Tracker with Integrated AI Assistant & Error Diagnostics

A complete full-stack web application designed for college students to organize assignments, track approaching deadlines, manage subjects, and receive instant AI assistance for FAQs, HTTP errors, and support tickets.

Built with **Python Django 6**, **SQLite / PostgreSQL** (SQL data & support tickets), **MongoDB** (chat logs & user feedback), and a modern, responsive frontend with a persistent floating AI assistant.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Nirmal61022/assignment-tracker)

---

## 📋 Assessment Submission Details

| Field | Detail |
|-------|--------|
| **1. Individual Task Title** | College Student Assignment Tracker with Integrated AI Assistant & Error Diagnostics |
| **2. Live Website Link (HTTPS)** | [https://assignment-tracker-nirmal.onrender.com](https://assignment-tracker-nirmal.onrender.com) *(or your deployed Render URL)* |
| **3. GitHub Repository Link** | [https://github.com/Nirmal61022/assignment-tracker](https://github.com/Nirmal61022/assignment-tracker) |

---

## ✅ Assessment Requirements & Feature Matrix

| Requirement | Implementation Detail | Location / Endpoint |
|-------------|-----------------------|---------------------|
| **Responsive multi-page website** | 8 responsive pages: Dashboard, Assignments, Calendar, Subjects, Profile, FAQs, Error Codes, Health Diagnostics | `/dashboard/`, `/assignments/`, `/calendar/`, etc. |
| **Chat widget on every page** | Persistent floating AI assistant widget embedded in `base.html`, accessible anywhere | Fixed bottom-right widget across all pages |
| **Minimum 10 FAQs in SQL** | 12 comprehensive FAQs stored in SQL database (`FAQ` model) with search & category filters | `/faqs/` |
| **Minimum 8 Error Codes** | 8 error codes cataloged: 400, 401, 403, 404, 429, 500, 503, and **Custom 488 (Assignment Submission Locked)** | `/error-codes/` |
| **Custom 404 & 500 pages** | Branded error pages with an interactive **"Ask the assistant"** button that pre-populates error queries | `/test-404/`, `/test-500/`, or any invalid URL |
| **AI Assistant Capabilities** | Answers from SQL FAQ data, explains all error codes, checks user deadlines, and offers ticket creation | Floating widget on all pages & `/api/chat/` |
| **Support Tickets in SQL** | `SupportTicket` model in SQL with ticket numbers, statuses, categories, priorities | `/tickets/` & `/api/tickets/create/` |
| **Chat logs & feedback in MongoDB** | `pymongo` integration saving conversations to `chat_logs` and student ratings to `feedback` (with resilient fallback) | `tracker/mongo.py` & `/api/feedback/` |
| **Secure API Keys & Env Vars** | All secrets and credentials loaded via `python-decouple` from `.env`; zero secrets in git | `.env.example`, `.gitignore` |
| **Request Logging & Health Check** | Middleware logging HTTP method, path, status, and duration; `/health/` monitoring SQL, Mongo, and APIs | `tracker/middleware.py` & `/health/` |
| **Third-Party API with Fallback** | Motivation Quote API with a strict **3.0-second timeout** and automatic offline curated fallback | `tracker/services.py` & Dashboard banner |
| **Automated Test Suite** | 38 comprehensive automated test cases covering auth, CRUD, FAQs, errors, health, and fallback | `python manage.py test tracker` (38/38 passed) |

---

## 💡 Proposed Improvement

### **Intelligent Calendar Sync (iCal/CalDAV) & Automated Multi-Channel Push Notifications**
Currently, students monitor deadlines through the in-app dashboard and calendar. A major future enhancement would be providing a dynamic **iCal / CalDAV subscription feed** (`/calendar/feed.ics?token=...`) allowing students to sync assignment deadlines directly with Google Calendar, Apple Calendar, and Outlook. Furthermore, adding **Web Push Notifications** (via Service Workers) and optional email reminders 24 hours before assignment cutoff times will ensure students never miss an urgent submission even when away from the web app.

---

## 🗄️ Database Architecture

### 1. SQL Database (SQLite local / PostgreSQL production)
* **`Subject`**: Course names, descriptions, and user color badges.
* **`Assignment`**: Title, subject relation, description, due date, priority, status, submission timestamp, computed `is_overdue` and `due_soon` properties.
* **`FAQ`**: 12 active student FAQs grouped into categories (Assignments, Deadlines, Subjects, Account, Errors).
* **`ErrorCode`**: 8 error codes (400, 401, 403, 404, 429, 500, 503, and site-specific 488).
* **`SupportTicket`**: User-reported or assistant-generated tickets with tracking numbers (`TICK-2026-XXXX`), priority, and resolution status.
* **`RequestLog`**: HTTP request latency and status audit log captured by middleware.

### 2. NoSQL Database (MongoDB Atlas / Live)
* **`chat_logs`**: Stores session ID, user ID, user prompt, assistant response, matched FAQ/Error ID, and timestamp.
* **`feedback`**: Stores student ratings (👍 / 👎) and qualitative comments on AI answers.
* *Resilience Feature:* If `MONGODB_URI` is omitted or MongoDB is unreachable, the system automatically falls back to an in-memory buffer without interrupting the student experience.

---

## 🤖 AI Assistant Capabilities

1. **FAQ Answering:** Searches the SQL database for relevant answers and presents formatted advice.
2. **Error Code Explanations:** Explains what HTTP 400-503 or custom 488 mean, lists common causes, and provides step-by-step resolution.
3. **Student Workload Summary:** Authenticated students can ask "What assignments are overdue?" or "How many assignments do I have?" for instant summaries.
4. **Automated Ticket Creation:** When a query cannot be answered or when the user requests human assistance, the assistant prompts to create a ticket stored directly in SQL.
5. **Feedback Loop:** Students can rate answers with thumbs up/down, which is logged into MongoDB.

---

## 🚀 Quick Start (Local Development)

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/Nirmal61022/assignment-tracker.git
cd assignment-tracker

pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your desired settings
```

### 3. Run Migrations & Seed Data
```bash
python manage.py migrate
python manage.py seed_demo
```
*Demo student credentials:*
* **Username:** `demo`
* **Password:** `demo123!`

### 4. Run Automated Tests
```bash
python manage.py test tracker
# Output: Ran 38 tests in ~24s ... OK
```

### 5. Start Development Server
```bash
python manage.py runserver
```
Visit: **http://127.0.0.1:8000**

---

## 🌐 Deploy to Render

1. Click the **Deploy to Render** button above or link your GitHub repository on [dashboard.render.com](https://dashboard.render.com).
2. Use the provided [`render.yaml`](render.yaml) blueprint or configure a Web Service:
   * **Build Command:** `./build.sh`
   * **Start Command:** `gunicorn config.wsgi:application`
3. Environment variables:
   * `SECRET_KEY`: *(Auto-generated)*
   * `DEBUG`: `False`
   * `ALLOWED_HOSTS`: `.onrender.com,localhost,127.0.0.1`
   * `CSRF_TRUSTED_ORIGINS`: `https://*.onrender.com`
   * `DATABASE_URL`: *(PostgreSQL connection string)*
   * `MONGODB_URI`: *(Optional: MongoDB Atlas connection string)*
   * `GEMINI_API_KEY`: *(Optional: Google Gemini API key)*

---

## 🧪 Verified Tests (38/38 Passing)

* `test_minimum_10_faqs_in_sql` — Passed
* `test_minimum_8_error_codes` — Passed (400, 401, 403, 404, 429, 500, 503, 488)
* `test_custom_site_specific_error_code_exists` — Passed
* `test_custom_404_view_rendered` — Passed (includes "Ask the Assistant")
* `test_custom_500_view_rendered` — Passed (includes "Ask the Assistant")
* `test_assistant_explains_error_404` — Passed
* `test_assistant_explains_custom_error_488` — Passed
* `test_assistant_answers_from_sql_faq` — Passed
* `test_assistant_suggests_ticket_when_unanswered` — Passed
* `test_support_ticket_creation_in_sql` — Passed
* `test_health_check_html` & `test_health_check_json` — Passed
* `test_third_party_motivation_service_with_fallback` — Passed
* `test_register_login_logout` — Passed
* `test_assignment_crud_and_overdue` — Passed
