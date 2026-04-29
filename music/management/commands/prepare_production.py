from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Q

from music.context_processors import PAGE_HEADER_DEFAULTS, PAGE_KEYWORD_DEFAULTS
from music.models import (
    Album,
    Announcement,
    Artist,
    Category,
    FAQ,
    LegalPage,
    ListeningHistory,
    PageBanner,
    Playlist,
    PostComment,
    QueueItem,
    SEOPage,
    SiteSettings,
    Track,
    TrackComment,
    UserPost,
    UserProfile,
    PAGE_CHOICES,
)


class Command(BaseCommand):
    help = "Remove demo content and normalize the platform for production handoff."

    demo_usernames = [
        "demo_admin",
        "demo_ahmad",
        "demo_sara",
        "demo_noura",
        "demo_guest",
    ]

    def handle(self, *args, **options):
        self.cleanup_demo_users()
        self.cleanup_demo_content()
        self.normalize_site_settings()
        self.normalize_seo_pages()
        self.stdout.write(self.style.SUCCESS("Production preparation completed successfully."))

    def cleanup_demo_users(self):
        user_model = get_user_model()
        QueueItem.objects.filter(user__username__in=self.demo_usernames).delete()
        ListeningHistory.objects.filter(user__username__in=self.demo_usernames).delete()
        TrackComment.objects.filter(user__username__in=self.demo_usernames).delete()
        PostComment.objects.filter(user__username__in=self.demo_usernames).delete()
        UserPost.objects.filter(user__username__in=self.demo_usernames).delete()
        Playlist.objects.filter(user__username__in=self.demo_usernames).delete()
        UserProfile.objects.filter(user__username__in=self.demo_usernames).delete()
        user_model.objects.filter(username__in=self.demo_usernames).delete()

    def cleanup_demo_content(self):
        Track.objects.filter(title__startswith="Demo ").delete()
        Album.objects.filter(title__startswith="Demo ").delete()
        Artist.objects.filter(name__startswith="Demo ").delete()
        Category.objects.filter(name__startswith="Demo ").delete()
        Playlist.objects.filter(name__startswith="Demo ").delete()
        Announcement.objects.filter(Q(title__startswith="Demo ") | Q(message__icontains="بيانات تجريبية")).delete()
        FAQ.objects.filter(Q(question__startswith="Demo ") | Q(answer__icontains="تجريبية")).delete()
        LegalPage.objects.filter(
            Q(title__startswith="Demo ")
            | Q(meta_title__startswith="Demo ")
            | Q(content__icontains="صفحة قانونية تجريبية")
        ).delete()
        SEOPage.objects.filter(
            Q(browser_title__startswith="Demo ")
            | Q(meta_keywords__icontains="demo")
            | Q(meta_keywords__icontains="test")
        ).delete()
        PageBanner.objects.filter(
            Q(title__startswith="Demo ")
            | Q(description__icontains="بنر تجريبي")
            | Q(eyebrow__icontains="تجربة جاهزة")
        ).delete()

    def normalize_site_settings(self):
        settings_obj = SiteSettings.load()
        if "example.com" in (settings_obj.canonical_domain or "") or "localhost" in (settings_obj.canonical_domain or ""):
            settings_obj.canonical_domain = ""
        if not settings_obj.site_name.strip():
            settings_obj.site_name = "نغَم"
        if not settings_obj.tagline.strip() or "تجريب" in settings_obj.tagline:
            settings_obj.tagline = "الأغاني بصوت صافي 100% بدون موسيقى"
        if not settings_obj.default_title.strip() or "تجريب" in settings_obj.default_title:
            settings_obj.default_title = "نغَم | أغاني بدون موسيقى بصوت صافي 100%"
        if not settings_obj.default_description.strip() or "تجريب" in settings_obj.default_description:
            settings_obj.default_description = (
                "نغَم منصة تقدّم لك الأغاني بصوت صافي 100% بدون موسيقى، "
                "جاهزة للسماع والمونتاج وصناعة المحتوى."
            )
        if not settings_obj.default_keywords.strip() or "demo" in settings_obj.default_keywords.lower():
            settings_obj.default_keywords = (
                "نغم, أغاني بدون موسيقى, أكابيلا عربي, صوت صافي, مونتاج, صناعة محتوى, صوت المغني الحقيقي"
            )
        if not settings_obj.header_cta_label.strip() or settings_obj.header_cta_label.lower() == "join":
            settings_obj.header_cta_label = "سو حسابك"
        if settings_obj.maintenance_message and "تجريب" in settings_obj.maintenance_message:
            settings_obj.maintenance_message = ""
        settings_obj.save()

    def normalize_seo_pages(self):
        page_labels = dict(PAGE_CHOICES)
        for page_key, label in PAGE_CHOICES:
            defaults = PAGE_HEADER_DEFAULTS.get(page_key, {})
            SEOPage.objects.update_or_create(
                page_key=page_key,
                defaults={
                    "browser_title": f"{page_labels.get(page_key, label)} | نغَم",
                    "meta_description": defaults.get(
                        "description",
                        "استكشف محتوى نغَم بصوت صافي وبدون موسيقى.",
                    ),
                    "meta_keywords": PAGE_KEYWORD_DEFAULTS.get(page_key, "نغم, صوت صافي, بدون موسيقى"),
                    "og_title": defaults.get("title", f"{label} | نغَم"),
                    "og_description": defaults.get(
                        "description",
                        "استكشف محتوى نغَم بصوت صافي وبدون موسيقى.",
                    ),
                    "noindex": False,
                },
            )
