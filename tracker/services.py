"""
Core Services for Assignment Tracker:
1. Third-party API integration with strict timeout and offline fallback.
2. AI Assistant response engine (FAQs, error codes, ticket generation).
"""
import re
import time
import random
import logging
import requests
from decouple import config

logger = logging.getLogger(__name__)

# Curated high-impact offline fallback study quotes & tips
OFFLINE_STUDY_MOTIVATIONS = [
    {
        "quote": "Action is the foundational key to all success. Start that assignment today.",
        "author": "Pablo Picasso",
        "category": "Productivity"
    },
    {
        "quote": "The secret of getting ahead is getting started. Break your complex tasks into small bite-sized steps.",
        "author": "Mark Twain",
        "category": "Time Management"
    },
    {
        "quote": "It always seems impossible until it's done.",
        "author": "Nelson Mandela",
        "category": "Perseverance"
    },
    {
        "quote": "Success is the sum of small efforts repeated day in and day out.",
        "author": "Robert Collier",
        "category": "Consistency"
    },
    {
        "quote": "Procrastination is the thief of time. Check your upcoming deadlines regularly.",
        "author": "Edward Young",
        "category": "Deadlines"
    },
    {
        "quote": "Focus on being productive instead of busy. Prioritize high-impact assignments.",
        "author": "Tim Ferriss",
        "category": "Focus"
    }
]


def get_third_party_motivation():
    """
    Calls a third-party Quote API with a strict 3.0 second timeout.
    Returns live result if online, or automatically falls back to curated study quotes.
    """
    api_url = "https://dummyjson.com/quotes/random"
    start_time = time.time()

    try:
        response = requests.get(api_url, timeout=3.0)
        duration_ms = round((time.time() - start_time) * 1000, 2)

        if response.status_code == 200:
            data = response.json()
            return {
                "quote": data.get("quote"),
                "author": data.get("author", "Unknown"),
                "source": "third_party_api_live",
                "api_status": "ok",
                "latency_ms": duration_ms,
                "is_fallback": False,
            }
    except Exception as e:
        logger.warning(f"Third-party Quote API failed or timed out ({e}). Using offline fallback.")

    # Graceful fallback selection
    fallback_item = random.choice(OFFLINE_STUDY_MOTIVATIONS)
    duration_ms = round((time.time() - start_time) * 1000, 2)
    return {
        "quote": fallback_item["quote"],
        "author": fallback_item["author"],
        "category": fallback_item["category"],
        "source": "curated_fallback_cache",
        "api_status": "fallback_triggered",
        "latency_ms": duration_ms,
        "is_fallback": True,
        "note": "Delivered via resilient offline fallback cache due to API timeout/policy."
    }


def check_third_party_api_health():
    """Diagnostic check for the third-party API used in /health/ page."""
    start = time.time()
    try:
        resp = requests.get("https://dummyjson.com/quotes/random", timeout=3.0)
        latency = round((time.time() - start) * 1000, 2)
        return {
            "status": "healthy" if resp.status_code == 200 else "degraded",
            "status_code": resp.status_code,
            "latency_ms": latency,
            "endpoint": "https://dummyjson.com/quotes/random",
            "fallback_ready": True
        }
    except Exception as e:
        latency = round((time.time() - start) * 1000, 2)
        return {
            "status": "fallback_active",
            "error": str(e),
            "latency_ms": latency,
            "endpoint": "https://dummyjson.com/quotes/random",
            "fallback_ready": True
        }


def process_assistant_message(user_message, user=None, context_code=None):
    """
    Intelligent AI Assistant response engine:
    1. Error code inquiry resolution (HTTP 400, 401, 403, 404, 429, 500, 503, custom 488).
    2. SQL FAQ knowledge base search.
    3. User-specific assignment status answers (if logged in).
    4. Gemini API enhancement if GEMINI_API_KEY is configured.
    5. Automatic support ticket trigger when question cannot be answered.
    """
    from tracker.models import FAQ, ErrorCode, Assignment, Subject
    msg_lower = user_message.strip().lower()

    # --- 1. Check for Error Code Inquiries ---
    # Check explicit context_code or extracted number
    error_num = None
    if context_code:
        try:
            error_num = int(context_code)
        except ValueError:
            pass

    if not error_num:
        # Search for patterns like 'error 404', 'code 500', '488', '403'
        code_matches = re.findall(r'\b(400|401|403|404|429|500|503|488)\b', msg_lower)
        if code_matches:
            error_num = int(code_matches[0])

    if error_num:
        err = ErrorCode.objects.filter(code=error_num).first()
        if err:
            badge = "🚨 Custom Site-Specific Error" if err.is_custom else "⚠️ Standard HTTP Error"
            response_text = (
                f"### {badge}: {err.code} — {err.name}\n\n"
                f"**Description:** {err.description}\n\n"
                f"**Common Causes:**\n{err.common_causes}\n\n"
                f"**Recommended Solution:**\n{err.solution}\n\n"
                f"*Need further technical help? You can create a support ticket directly below.*"
            )
            return {
                "reply": response_text,
                "matched_type": "error_code",
                "matched_id": err.id,
                "can_create_ticket": True,
                "suggested_actions": ["Create Support Ticket", "View All Error Codes", "Check System Health"],
            }

    # --- 2. Check for User Data Inquiries (if authenticated) ---
    if user and user.is_authenticated:
        if any(w in msg_lower for w in ["my assignment", "how many assignment", "pending", "overdue", "my status", "summary"]):
            assignments = Assignment.objects.filter(user=user)
            total = assignments.count()
            submitted = assignments.filter(status='submitted').count()
            overdue_count = sum(1 for a in assignments if a.is_overdue)
            due_soon_count = sum(1 for a in assignments if a.due_soon)
            pending_count = total - submitted

            reply = (
                f"Here is your current assignment overview, **{user.username}**:\n\n"
                f"- 📊 **Total Assignments:** {total}\n"
                f"- ⏳ **Pending / In Progress:** {pending_count}\n"
                f"- ✅ **Submitted:** {submitted}\n"
                f"- 🚨 **Overdue:** {overdue_count}\n"
                f"- ⚠️ **Due Soon (within 48h):** {due_soon_count}\n\n"
                f"You can view and manage all assignments from your [All Assignments page](/assignments/)."
            )
            return {
                "reply": reply,
                "matched_type": "user_data",
                "matched_id": None,
                "can_create_ticket": False,
                "suggested_actions": ["View Assignments", "View Calendar", "Ask FAQ"],
            }

    # --- 3. Search SQL FAQs ---
    all_faqs = FAQ.objects.filter(is_active=True)
    best_faq = None
    best_score = 0

    # Tokenize user query
    clean_words = set(re.findall(r'\b[a-z]{3,}\b', msg_lower))
    stopwords = {"what", "when", "where", "how", "why", "who", "the", "and", "can", "for", "with", "this", "that", "does", "are"}
    query_keywords = clean_words - stopwords

    for faq in all_faqs:
        faq_text = (faq.question + " " + faq.answer + " " + faq.category).lower()
        faq_keywords = set(re.findall(r'\b[a-z]{3,}\b', faq_text))
        overlap = len(query_keywords.intersection(faq_keywords))

        # Check for phrase or exact question match
        if faq.question.lower() in msg_lower or msg_lower in faq.question.lower():
            overlap += 10

        if overlap > best_score:
            best_score = overlap
            best_faq = faq

    # Confidence threshold
    if best_faq and best_score >= 2:
        reply = (
            f"**FAQ: {best_faq.question}**\n\n"
            f"{best_faq.answer}\n\n"
            f"*Category: {best_faq.category}*"
        )
        return {
            "reply": reply,
            "matched_type": "faq",
            "matched_id": best_faq.id,
            "can_create_ticket": False,
            "suggested_actions": ["Ask another question", "Browse All FAQs", "Contact Support"],
        }

    # --- 4. Check for Ticket / Help request keywords ---
    if any(phrase in msg_lower for phrase in ["ticket", "support", "human", "contact", "bug", "help me", "agent"]):
        return {
            "reply": (
                "I am here to help! If you have encountered a bug or need support from an administrator, "
                "I can create a support ticket for you right away. "
                "Click the **Create Support Ticket** button below or fill in your ticket details."
            ),
            "matched_type": "ticket_prompt",
            "matched_id": None,
            "can_create_ticket": True,
            "suggested_actions": ["Create Support Ticket", "Browse FAQs", "View Error Codes"],
        }

    # --- 5. Try Gemini LLM if API Key is configured ---
    gemini_key = config('GEMINI_API_KEY', default='').strip()
    if gemini_key:
        try:
            # Build context from top 5 FAQs and error codes
            context_faqs = "\n".join([f"Q: {f.question} A: {f.answer}" for f in all_faqs[:6]])
            err_codes = "\n".join([f"{e.code} ({e.name}): {e.description} Solution: {e.solution}" for e in ErrorCode.objects.all()[:8]])

            prompt = (
                f"You are the AI Assistant for the college Assignment Tracker web app.\n"
                f"Use this knowledge base to answer the student concisely:\n\n"
                f"FAQS:\n{context_faqs}\n\n"
                f"ERROR CODES:\n{err_codes}\n\n"
                f"Student Question: {user_message}\n"
                f"If the question cannot be answered from the knowledge base, kindly say you don't have that information and invite them to create a support ticket."
            )

            headers = {"Content-Type": "application/json"}
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 300}
            }
            res = requests.post(url, headers=headers, json=payload, timeout=4.0)
            if res.status_code == 200:
                ai_reply = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                return {
                    "reply": ai_reply,
                    "matched_type": "gemini_ai",
                    "matched_id": None,
                    "can_create_ticket": True,
                    "suggested_actions": ["Was this helpful?", "Browse FAQs", "Create Support Ticket"],
                }
        except Exception as e:
            logger.warning(f"Gemini API call failed or timed out: {e}")

    # --- 6. Fallback when query cannot be answered ---
    return {
        "reply": (
            "I'm sorry, but I couldn't find a direct answer in our FAQs or error code database for that question.\n\n"
            "Would you like me to **create a support ticket** for you? "
            "Our support team can look into this directly and get back to you."
        ),
        "matched_type": "unanswered",
        "matched_id": None,
        "can_create_ticket": True,
        "suggested_actions": ["Create Support Ticket", "Browse FAQs", "View Error Codes"],
    }
