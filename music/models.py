from django.conf import settings
from django.core.cache import cache
from django.db import models


PAGE_CHOICES = [
    ("home", "الرئيسية"),
    ("discover", "اكتشف"),
    ("charts", "الأكثر استماعًا"),
    ("library", "مكتبتي"),
    ("favorites", "المفضلة"),
    ("search", "البحث"),
    ("artists", "الفنانون"),
    ("artist_detail", "صفحة الفنان"),
    ("albums", "الألبومات"),
    ("album_detail", "صفحة الألبوم"),
    ("categories", "التصنيفات"),
    ("category_detail", "صفحة التصنيف"),
    ("playlists", "قوائم التشغيل"),
    ("playlist_detail", "صفحة قائمة التشغيل"),
    ("track_detail", "صفحة المقطع"),
    ("login", "تسجيل الدخول"),
    ("signup", "إنشاء حساب"),
    ("profile_detail", "الملف الشخصي"),
    ("profile_edit", "تعديل الملف الشخصي"),
    ("legal_pages", "الصفحات القانونية"),
    ("legal_page_detail", "صفحة قانونية"),
]


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    cover = models.ImageField(upload_to="categories/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class SiteSettings(models.Model):
    site_name = models.CharField(max_length=120, default="نغَم")
    tagline = models.CharField(max_length=200, default="الأغاني بصوت صافي 100% — بدون موسيقى")
    default_title = models.CharField(max_length=180, default="نغَم | أغاني بدون موسيقى بصوت صافي 100%")
    default_description = models.TextField(
        default="نغَم منصة تقدّم لك الأغاني بصوت صافي 100% بدون موسيقى. اسمع صوت المغني الحقيقي بجودة عالية للمتعة أو للمونتاج وصناعة المحتوى."
    )
    default_keywords = models.CharField(
        max_length=300,
        blank=True,
        default="نغَم, أغاني بدون موسيقى, أكابيلا عربي, Acapella, صوت صافي, صوت المغني الحقيقي, مونتاج, صناعة محتوى, أغاني للمونتاج, أغاني أكابيلا",
        help_text="افصل الكلمات بفواصل."
    )
    logo = models.ImageField(upload_to="branding/", null=True, blank=True)
    favicon = models.ImageField(upload_to="branding/", null=True, blank=True)
    og_image = models.ImageField(upload_to="seo/", null=True, blank=True)
    canonical_domain = models.URLField(blank=True, help_text="مثال: https://nagham.example.com")
    analytics_code = models.TextField(blank=True, help_text="كود Analytics اختياري.")
    header_cta_label = models.CharField(max_length=80, default="جرّب الآن")
    header_cta_url = models.CharField(max_length=200, default="/signup/")
    maintenance_message = models.CharField(max_length=240, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self):
        return self.site_name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete("site_settings_singleton")
        cache.delete("dashboard:settings:v1")
        cache.delete("dashboard:settings:v2")

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SEOPage(models.Model):
    page_key = models.CharField(max_length=80, choices=PAGE_CHOICES, unique=True)
    browser_title = models.CharField(max_length=180)
    meta_description = models.TextField(max_length=320, blank=True)
    meta_keywords = models.CharField(max_length=300, blank=True)
    og_title = models.CharField(max_length=180, blank=True)
    og_description = models.TextField(max_length=320, blank=True)
    og_image = models.ImageField(upload_to="seo/", null=True, blank=True)
    noindex = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["page_key"]

    def __str__(self):
        return self.get_page_key_display()


class PageBanner(models.Model):
    PLACEMENT_CHOICES = [
        ("top", "Top"),
        ("after_hero", "After hero"),
        ("after_section_1", "After section 1"),
        ("after_section_2", "After section 2"),
        ("after_section_3", "After section 3"),
        ("bottom", "Bottom"),
    ]
    SIZE_CHOICES = [
        ("hero", "Hero"),
        ("wide", "Wide"),
        ("split", "Split"),
        ("compact", "Compact"),
    ]

    page_key = models.CharField(max_length=80, choices=PAGE_CHOICES)
    sort_order = models.PositiveIntegerField(default=0)
    placement = models.CharField(max_length=40, choices=PLACEMENT_CHOICES, default="top")
    size = models.CharField(max_length=20, choices=SIZE_CHOICES, default="hero")
    eyebrow = models.CharField(max_length=80, blank=True)
    title = models.CharField(max_length=180)
    description = models.TextField(max_length=320, blank=True)
    image = models.ImageField(upload_to="banners/", null=True, blank=True)
    image_url = models.URLField(blank=True, help_text="رابط صورة مباشر من الإنترنت (اختياري).")
    primary_label = models.CharField(max_length=80, blank=True)
    primary_url = models.CharField(max_length=200, blank=True)
    secondary_label = models.CharField(max_length=80, blank=True)
    secondary_url = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["page_key", "placement", "sort_order", "id"]
        verbose_name = "Page banner"
        verbose_name_plural = "Page banners"

    def __str__(self):
        return f"{self.get_page_key_display()} - {self.title}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete(f"page_banners::{self.page_key}")
        cache.delete("dashboard:seo:v1")
        cache.delete("dashboard:settings:v1")
        cache.delete("dashboard:media:v1")


class LegalPage(models.Model):
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True)
    summary = models.CharField(max_length=260, blank=True)
    content = models.TextField()
    meta_title = models.CharField(max_length=180, blank=True)
    meta_description = models.TextField(max_length=320, blank=True)
    is_published = models.BooleanField(default=True)
    show_in_footer = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class Announcement(models.Model):
    title = models.CharField(max_length=140)
    message = models.CharField(max_length=260)
    link_label = models.CharField(max_length=80, blank=True)
    link_url = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class FAQ(models.Model):
    question = models.CharField(max_length=220)
    answer = models.TextField()
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question


class Artist(models.Model):
    name = models.CharField(max_length=200)
    image = models.ImageField(upload_to="artists/", null=True, blank=True)
    bio = models.TextField(blank=True)
    verified = models.BooleanField(default=False)
    followers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="followed_artists"
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Album(models.Model):
    title = models.CharField(max_length=200)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="albums")
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="albums"
    )
    cover = models.ImageField(upload_to="albums/", null=True, blank=True)
    description = models.TextField(blank=True)
    release_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-release_date", "-created_at"]

    def __str__(self):
        return self.title


class Track(models.Model):
    MOOD_CHOICES = [
        ("calm", "هادئ"),
        ("faith", "إيماني"),
        ("morning", "صباحي"),
        ("focus", "تركيز"),
        ("kids", "للأطفال"),
    ]

    title = models.CharField(max_length=200)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="tracks")
    album = models.ForeignKey(
        Album, on_delete=models.SET_NULL, null=True, blank=True, related_name="tracks"
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="tracks"
    )
    audio_file = models.FileField(upload_to="tracks/")
    cover = models.ImageField(upload_to="covers/", null=True, blank=True)
    description = models.TextField(blank=True)
    lyrics = models.TextField(blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    mood = models.CharField(max_length=20, choices=MOOD_CHOICES, blank=True)
    views = models.PositiveIntegerField(default=0)
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="liked_tracks"
    )
    saved_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="saved_tracks"
    )
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    allow_download = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["-views"]),
            models.Index(fields=["is_published"]),
        ]

    def __str__(self):
        return self.title

    @property
    def duration_label(self):
        if not self.duration_seconds:
            return "غير محدد"
        minutes, seconds = divmod(self.duration_seconds, 60)
        return f"{minutes}:{seconds:02d}"


class Playlist(models.Model):
    name = models.CharField(max_length=200)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="playlists"
    )
    tracks = models.ManyToManyField(Track, blank=True, related_name="playlists")
    description = models.TextField(blank=True)
    cover = models.ImageField(upload_to="playlists/", null=True, blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name


class ListeningHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="listening_history",
    )
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="plays")
    session_key = models.CharField(max_length=40, blank=True)
    played_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-played_at"]
        verbose_name_plural = "listening history"

    def __str__(self):
        return f"{self.track} at {self.played_at:%Y-%m-%d %H:%M}"


class QueueItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="queue_items"
    )
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="queued_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        unique_together = ("user", "track")

    def __str__(self):
        return f"{self.user} - {self.track}"


class TrackComment(models.Model):
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="track_comments"
    )
    body = models.TextField(max_length=600)
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} on {self.track}"


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    display_name = models.CharField(max_length=120, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to="profiles/avatars/", null=True, blank=True)
    banner_image = models.ImageField(upload_to="profiles/banners/", null=True, blank=True)
    location = models.CharField(max_length=120, blank=True)
    website = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return self.display_name or self.user.username

    @property
    def name(self):
        return self.display_name or self.user.get_username()


class UserPost(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts"
    )
    body = models.TextField(max_length=1200)
    image = models.ImageField(upload_to="posts/", null=True, blank=True)
    shared_track = models.ForeignKey(
        Track,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shared_posts",
    )
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="liked_posts",
    )
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["-created_at"]), models.Index(fields=["is_published"])]

    def __str__(self):
        return f"{self.user} - {self.created_at:%Y-%m-%d}"


class PostComment(models.Model):
    post = models.ForeignKey(UserPost, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="post_comments"
    )
    body = models.TextField(max_length=600)
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["-created_at"]), models.Index(fields=["is_visible"])]

    def __str__(self):
        return f"{self.user} on {self.post_id}"


class SecurityEvent(models.Model):
    SEVERITY_CHOICES = [
        ("low", "منخفض"),
        ("medium", "متوسط"),
        ("high", "مرتفع"),
    ]

    ip_address = models.GenericIPAddressField()
    path = models.CharField(max_length=500)
    user_agent = models.TextField(blank=True)
    reason = models.CharField(max_length=200)
    severity = models.CharField(max_length=12, choices=SEVERITY_CHOICES, default="medium")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["ip_address", "-created_at"]),
            models.Index(fields=["severity", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.ip_address} - {self.reason}"


class BlockedIP(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    reason = models.CharField(max_length=200)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["ip_address", "is_active"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.ip_address} - {self.reason}"


class VisitEvent(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="visit_events",
    )
    path = models.CharField(max_length=500)
    method = models.CharField(max_length=8, default="GET")
    status_code = models.PositiveSmallIntegerField(default=200)
    response_ms = models.PositiveIntegerField(default=0)
    ip_address = models.GenericIPAddressField()
    country_code = models.CharField(max_length=8, blank=True)
    user_agent = models.TextField(blank=True)
    referer = models.CharField(max_length=500, blank=True)
    is_staff_request = models.BooleanField(default=False)
    visited_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-visited_at"]
        indexes = [
            models.Index(fields=["-visited_at"]),
            models.Index(fields=["ip_address", "-visited_at"]),
            models.Index(fields=["country_code", "-visited_at"]),
            models.Index(fields=["path", "-visited_at"]),
        ]

    def __str__(self):
        return f"{self.path} - {self.ip_address}"
