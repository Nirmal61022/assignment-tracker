"""
Request Logging Middleware for Assignment Tracker.
Logs HTTP request duration, method, path, status, and IP for monitoring and health check diagnostics.
"""
import time
import logging

logger = logging.getLogger('tracker.requests')


class RequestLoggingMiddleware:
    """Logs non-static HTTP requests to the SQL database."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        response = self.get_response(request)

        duration_ms = (time.time() - start_time) * 1000.0

        # Skip noisy asset paths
        path = request.path
        if not (path.startswith('/static/') or path == '/favicon.ico'):
            self._log_request(request, response, duration_ms)

        # Attach response time header for debugging
        response['X-Response-Time-Ms'] = f"{duration_ms:.2f}"
        return response

    def _log_request(self, request, response, duration_ms):
        try:
            from tracker.models import RequestLog

            # Extract client IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR')

            user_agent = request.META.get('HTTP_USER_AGENT', '')[:300]

            RequestLog.objects.create(
                method=request.method,
                path=request.path[:500],
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
                ip_address=ip if ip and len(ip) <= 45 else None,
                user_agent=user_agent,
            )

            # Cap log count at 1,000 to keep SQL database lightweight
            if RequestLog.objects.count() > 1000:
                old_ids = RequestLog.objects.order_by('-timestamp').values_list('id', flat=True)[800:]
                RequestLog.objects.filter(id__in=list(old_ids)).delete()

        except Exception as e:
            logger.debug(f"Request logging error: {e}")
