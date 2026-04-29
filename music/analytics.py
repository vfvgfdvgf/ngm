import time

from django.core.cache import cache

from .models import VisitEvent
from .security import get_client_ip


TRACKABLE_PREFIX_SKIP = (
    "/static/",
    "/media/",
    "/favicon.ico",
    "/robots.txt",
    "/sitemap.xml",
)


class VisitTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)

        if self._should_track(request, response):
            duration_ms = max(1, int((time.perf_counter() - start) * 1000))
            self._track_visit(request, response.status_code, duration_ms)

        return response

    def _should_track(self, request, response):
        path = request.path or "/"
        if request.method != "GET":
            return False
        if path.startswith(TRACKABLE_PREFIX_SKIP):
            return False
        if response.status_code >= 500:
            return False
        content_type = response.get("Content-Type", "")
        return "text/html" in content_type

    def _track_visit(self, request, status_code, duration_ms):
        ip_address = get_client_ip(request)
        user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
        country_code = (
            request.META.get("HTTP_CF_IPCOUNTRY")
            or request.META.get("HTTP_X_COUNTRY_CODE")
            or request.META.get("HTTP_X_COUNTRY")
            or ""
        ).strip().upper()[:8]
        referer = (request.META.get("HTTP_REFERER") or "")[:500]
        user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:500]
        is_staff_request = bool(user and user.is_staff)

        burst_key = f"analytics:visit:{ip_address}:{request.path}"
        if cache.get(burst_key):
            return
        cache.set(burst_key, True, 20)

        VisitEvent.objects.create(
            user=user,
            path=(request.path or "/")[:500],
            method=request.method[:8],
            status_code=status_code,
            response_ms=duration_ms,
            ip_address=ip_address,
            country_code=country_code,
            user_agent=user_agent,
            referer=referer,
            is_staff_request=is_staff_request,
        )
