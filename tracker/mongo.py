"""
MongoDB Integration for Chat Logs and Feedback.
Provides seamless logging into MongoDB with resilient fallback when MongoDB is offline.
"""
import logging
import time
from datetime import datetime, timezone
from decouple import config

logger = logging.getLogger(__name__)

# Cache client connection
_mongo_client = None
_fallback_logs = []
_fallback_feedback = []


def get_mongo_client():
    """Retrieve or initialize MongoDB client if MONGODB_URI is configured."""
    global _mongo_client
    uri = config('MONGODB_URI', default='').strip()
    if not uri:
        return None

    if _mongo_client is None:
        try:
            from pymongo import MongoClient
            _mongo_client = MongoClient(uri, serverSelectionTimeoutMS=2000, connectTimeoutMS=2000)
            # Test connection with a quick ping
            _mongo_client.admin.command('ping')
        except Exception as e:
            logger.warning(f"MongoDB connection failed: {e}. Falling back to in-memory logging.")
            return None
    return _mongo_client


def get_mongo_db():
    """Return MongoDB database or None if unavailable."""
    client = get_mongo_client()
    if client:
        db_name = config('MONGODB_DB', default='assignment_tracker')
        return client[db_name]
    return None


def log_chat_message(session_id, user_id, username, user_message, assistant_response, metadata=None):
    """
    Log chat conversation into MongoDB collection 'chat_logs'.
    Falls back gracefully if MongoDB is unavailable.
    """
    doc = {
        'session_id': session_id,
        'user_id': user_id,
        'username': username or 'Anonymous',
        'user_message': user_message,
        'assistant_response': assistant_response,
        'metadata': metadata or {},
        'timestamp': datetime.now(timezone.utc),
    }

    try:
        db = get_mongo_db()
        if db is not None:
            result = db['chat_logs'].insert_one(doc)
            doc['_id'] = str(result.inserted_id)
            return True, str(result.inserted_id)
    except Exception as e:
        logger.error(f"Failed to log chat to MongoDB: {e}")

    # Fallback storage
    doc['_id'] = f"fallback_{len(_fallback_logs) + 1}"
    _fallback_logs.append(doc)
    if len(_fallback_logs) > 200:
        _fallback_logs.pop(0)
    return False, doc['_id']


def save_feedback(session_id, message_id, rating, comment='', user_id=None):
    """
    Save student feedback on assistant responses into MongoDB collection 'feedback'.
    """
    doc = {
        'session_id': session_id,
        'message_id': message_id,
        'rating': rating,  # 'up', 'down', 1-5
        'comment': comment,
        'user_id': user_id,
        'timestamp': datetime.now(timezone.utc),
    }

    try:
        db = get_mongo_db()
        if db is not None:
            result = db['feedback'].insert_one(doc)
            return True, str(result.inserted_id)
    except Exception as e:
        logger.error(f"Failed to save feedback to MongoDB: {e}")

    _fallback_feedback.append(doc)
    if len(_fallback_feedback) > 100:
        _fallback_feedback.pop(0)
    return False, f"fallback_{len(_fallback_feedback)}"


def check_mongo_connection():
    """
    Diagnostics check for MongoDB used in the /health/ endpoint.
    Returns status dict with connection state, latency, and collection counts.
    """
    uri = config('MONGODB_URI', default='').strip()
    if not uri:
        return {
            'status': 'not_configured',
            'configured': False,
            'connected': False,
            'message': 'MONGODB_URI not configured in environment variables (operating with local buffer)',
            'chat_logs_count': len(_fallback_logs),
            'feedback_count': len(_fallback_feedback),
            'storage_mode': 'fallback_memory'
        }

    start = time.time()
    try:
        from pymongo import MongoClient
        test_client = MongoClient(uri, serverSelectionTimeoutMS=2000, connectTimeoutMS=2000)
        test_client.admin.command('ping')
        latency_ms = round((time.time() - start) * 1000, 2)
        db_name = config('MONGODB_DB', default='assignment_tracker')
        db = test_client[db_name]
        logs_count = db['chat_logs'].count_documents({})
        feedback_count = db['feedback'].count_documents({})

        return {
            'status': 'healthy',
            'configured': True,
            'connected': True,
            'latency_ms': latency_ms,
            'database': db_name,
            'chat_logs_count': logs_count,
            'feedback_count': feedback_count,
            'storage_mode': 'mongodb_live'
        }
    except Exception as e:
        return {
            'status': 'degraded',
            'configured': True,
            'connected': False,
            'error': str(e),
            'message': 'MongoDB configured but unreachable (operating with fallback buffer)',
            'chat_logs_count': len(_fallback_logs),
            'feedback_count': len(_fallback_feedback),
            'storage_mode': 'fallback_memory'
        }
