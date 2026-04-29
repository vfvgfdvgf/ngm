import ipaddress
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import render
from django.utils import timezone

from .models import BlockedIP, SecurityEvent


SUSPICIOUS_PATH_PARTS = (
    ".env",
    ".git",
    "wp-admin",
    "wp-login",
    "phpmyadmin",
    "adminer",
    "vendor/phpunit",
    "server-status",
    "cgi-bin",
    "actuator",
    "_ignition",
    "boaform",
    "HNAP1",
    "etc/passwd",
)

SUSPICIOUS_USER_AGENTS = (
    "sqlmap",
    "nikto",
    "nmap",
    "masscan",
    "gobuster",
    "dirbuster",
    "dirb",
    "wpscan",
    "nessus",
    "whatweb",
    "zgrab",
)

SAFE_PREFIXES = ("/static/", "/media/", "/favicon.ico", "/admin/jsi18n/")


def get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or "0.0.0.0"


class SecurityMonitorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip_address = get_client_ip(request)
        user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:500]
        path = (request.path or "")[:500]

        if self._should_bypass_security(ip_address, path):
            return self.get_response(request)

        blocked_reason = self._get_active_block(ip_address)
        if blocked_reason:
            return self._deny(request, blocked_reason)

        suspicious_reason = self._detect_suspicious_request(path, user_agent)
        if suspicious_reason:
            self._record_event(ip_address, path, user_agent, suspicious_reason, severity="high")
            self._block_ip(ip_address, suspicious_reason, minutes=120)
            return self._deny(request, suspicious_reason)

        if self._is_aggressive_request_burst(ip_address):
            reason = "عدد مرتفع وغير اعتيادي من الطلبات خلال فترة قصيرة"
            self._record_event(ip_address, path, user_agent, reason, severity="medium")
            self._block_ip(ip_address, reason, minutes=30)
            return self._deny(request, reason)

        response = self.get_response(request)

        if response.status_code == 404 and self._is_suspicious_path_probe(path):
            reason = "محاولة استكشاف مسارات أو ملفات حساسة"
            self._record_event(ip_address, path, user_agent, reason, severity="high")
            self._block_ip(ip_address, reason, minutes=120)

        return response

    def _detect_suspicious_request(self, path, user_agent):
        normalized_path = path.lower()
        normalized_agent = user_agent.lower()

        if any(marker in normalized_path for marker in SUSPICIOUS_PATH_PARTS):
            return "محاولة الوصول إلى مسارات أو ملفات معروفة بالاستكشاف العدائي"

        if any(marker in normalized_agent for marker in SUSPICIOUS_USER_AGENTS):
            return "تم رصد أداة فحص أو نمط آلي غير اعتيادي في الترويسة"

        return ""

    def _should_bypass_security(self, ip_address, path):
        if path.startswith(SAFE_PREFIXES):
            return True

        if settings.DEBUG and self._is_private_or_local_ip(ip_address):
            return True

        return False

    def _is_private_or_local_ip(self, ip_address):
        try:
            parsed = ipaddress.ip_address(ip_address)
        except ValueError:
            return False
        return parsed.is_loopback or parsed.is_private

    def _is_suspicious_path_probe(self, path):
        normalized_path = path.lower()
        return any(marker in normalized_path for marker in SUSPICIOUS_PATH_PARTS)

    def _is_aggressive_request_burst(self, ip_address):
        cache_key = f"security:burst:{ip_address}"
        count = cache.get(cache_key, 0) + 1
        cache.set(cache_key, count, 60)
        return count >= 160

    def _get_active_block(self, ip_address):
        cache_key = f"security:blocked:{ip_address}"
        cached_reason = cache.get(cache_key)
        if cached_reason:
            return cached_reason

        now = timezone.now()
        blocked = (
            BlockedIP.objects.filter(ip_address=ip_address, is_active=True, expires_at__gt=now)
            .order_by("-updated_at")
            .first()
        )
        if not blocked:
            return ""

        cache.set(cache_key, blocked.reason, int((blocked.expires_at - now).total_seconds()))
        return blocked.reason

    def _record_event(self, ip_address, path, user_agent, reason, severity="medium"):
        SecurityEvent.objects.create(
            ip_address=ip_address,
            path=path,
            user_agent=user_agent,
            reason=reason,
            severity=severity,
        )

    def _block_ip(self, ip_address, reason, minutes=30):
        expires_at = timezone.now() + timedelta(minutes=minutes)
        blocked, _ = BlockedIP.objects.update_or_create(
            ip_address=ip_address,
            defaults={
                "reason": reason,
                "expires_at": expires_at,
                "is_active": True,
            },
        )
        ttl = max(60, int((blocked.expires_at - timezone.now()).total_seconds()))
        cache.set(f"security:blocked:{ip_address}", blocked.reason, ttl)

    def _deny(self, request, reason):
        response = render(
            request,
            "security_blocked.html",
            {"block_reason": reason},
            status=403,
        )
        response["Cache-Control"] = "no-store"
        return response
