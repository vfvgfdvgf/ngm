from django.contrib import admin
from django.utils.html import format_html, format_html_join

from .models import (
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
    SecurityEvent,
    SEOPage,
    SiteSettings,
    BlockedIP,
    Track,
    TrackComment,
    UserPost,
    UserProfile,
    VisitEvent,
)


admin.site.site_header = "ظ„ظˆط­ط© طھط­ظƒظ… ظ†ط؛ظ…"
admin.site.site_title = "ظ†ط؛ظ…"
admin.site.index_title = "ط¥ط¯ط§ط±ط© ظ…ظ†طµط© ظ†ط؛ظ…"


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("ط§ظ„ظ‡ظˆظٹط©", {"fields": ("site_name", "tagline", "logo", "favicon", "branding_preview", "header_cta_label", "header_cta_url")}),
        (
            "SEO ط§ظ„ط§ظپطھط±ط§ط¶ظٹ",
            {"fields": ("default_title", "default_description", "default_keywords", "og_image", "canonical_domain")},
        ),
        ("ط£ظƒظˆط§ط¯ ظˆطھظ†ط¨ظٹظ‡ط§طھ", {"fields": ("analytics_code", "maintenance_message")}),
    )
    readonly_fields = ("branding_preview",)

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="ظ…ط¹ط§ظٹظ†ط© ط§ظ„ط´ط¹ط§ط± ظˆط§ظ„ط£ظٹظ‚ظˆظ†ط©")
    def branding_preview(self, obj):
        if not obj:
            return "ط§ط­ظپط¸ ط§ظ„ط¥ط¹ط¯ط§ط¯ط§طھ ط£ظˆظ„ظ‹ط§ ظ„ط¹ط±ط¶ ط§ظ„ظ…ط¹ط§ظٹظ†ط©."

        previews = []
        if obj.logo:
            previews.append(
                format_html(
                    '<div style="display:grid;gap:8px;"><strong>ط§ظ„ط´ط¹ط§ط±</strong><img src="{}" alt="Logo preview" style="max-width:220px;max-height:88px;object-fit:contain;border-radius:18px;padding:14px;background:linear-gradient(135deg,#fff7f1,#f7e3d6);border:1px solid #e7d6ca;box-shadow:0 12px 24px -18px rgba(0,0,0,.35);" /></div>',
                    obj.logo.url,
                )
            )
        if obj.favicon:
            previews.append(
                format_html(
                    '<div style="display:grid;gap:8px;"><strong>Favicon</strong><img src="{}" alt="Favicon preview" style="width:56px;height:56px;object-fit:contain;border-radius:16px;padding:10px;background:linear-gradient(135deg,#fff7f1,#f7e3d6);border:1px solid #e7d6ca;box-shadow:0 12px 24px -18px rgba(0,0,0,.35);" /></div>',
                    obj.favicon.url,
                )
            )

        if not previews:
            return "ظ„ط§ ظٹظˆط¬ط¯ ط´ط¹ط§ط± ط£ظˆ favicon ظ…ط±ظپظˆط¹ط§ظ† ط¨ط¹ط¯."

        return format_html(
            '<div style="display:flex;flex-wrap:wrap;gap:18px;align-items:flex-start;">{}</div>',
            format_html_join("", "{}", ((preview,) for preview in previews)),
        )


@admin.register(SEOPage)
class SEOPageAdmin(admin.ModelAdmin):
    list_display = ("page_key", "browser_title", "noindex", "updated_at")
    list_filter = ("noindex", "page_key")
    search_fields = ("browser_title", "meta_description", "meta_keywords")


@admin.register(PageBanner)
class PageBannerAdmin(admin.ModelAdmin):
    list_display = ("page_key", "placement", "size", "title", "sort_order", "is_active", "updated_at")
    list_filter = ("is_active", "page_key")
    search_fields = ("title", "description", "primary_label", "secondary_label")
    list_editable = ("sort_order", "is_active")
    readonly_fields = ("image_preview",)
    fieldsets = (
        ("ط§ظ„ظ…ط­طھظˆظ‰", {"fields": ("page_key", "placement", "size", "sort_order", "eyebrow", "title", "description", "is_active")}),
        ("ط§ظ„طµظˆط±ط©", {"fields": ("image", "image_url", "image_preview")}),
        ("ط§ظ„ط£ط²ط±ط§ط±", {"fields": ("primary_label", "primary_url", "secondary_label", "secondary_url")}),
    )

    @admin.display(description="ظ…ط¹ط§ظٹظ†ط© ط§ظ„طµظˆط±ط©")
    def image_preview(self, obj):
        if not obj:
            return "ط§ط­ظپط¸ ط§ظ„ط¨ظ†ط± ط£ظˆظ„ط§ظ‹ ظ„ط¹ط±ط¶ ط§ظ„ظ…ط¹ط§ظٹظ†ط©."
        image_url = obj.image.url if obj.image else obj.image_url
        if not image_url:
            return "ظ„ط§ طھظˆط¬ط¯ طµظˆط±ط© ط¨ط¹ط¯."
        return format_html(
            '<img src="{}" alt="Banner preview" style="max-width: min(100%, 360px); border-radius: 18px; border: 1px solid #ddd; box-shadow: 0 12px 24px -18px rgba(0,0,0,.35);" />',
            image_url,
        )


@admin.register(LegalPage)
class LegalPageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published", "show_in_footer", "updated_at")
    list_filter = ("is_published", "show_in_footer", "updated_at")
    search_fields = ("title", "summary", "content", "meta_description")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "starts_at", "ends_at", "created_at")
    list_filter = ("is_active", "starts_at", "ends_at")
    search_fields = ("title", "message")


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("question", "answer")
    list_editable = ("is_active", "sort_order")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name", "description")


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ("name", "verified", "followers_count")
    search_fields = ("name", "bio")
    list_filter = ("verified",)

    @admin.display(description="ط§ظ„ظ…طھط§ط¨ط¹ظˆظ†")
    def followers_count(self, obj):
        return obj.followers.count()


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ("title", "artist", "category", "release_date", "created_at")
    search_fields = ("title", "artist__name", "description")
    list_filter = ("category", "release_date", "created_at")


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "artist",
        "category",
        "mood",
        "views",
        "likes_count",
        "is_featured",
        "is_published",
        "created_at",
    )
    list_filter = ("category", "mood", "is_featured", "is_published", "created_at")
    search_fields = ("title", "artist__name", "album__title", "description", "lyrics")
    autocomplete_fields = ("artist", "album", "category")
    filter_horizontal = ("likes", "saved_by")

    @admin.display(description="ط§ظ„ط¥ط¹ط¬ط§ط¨ط§طھ")
    def likes_count(self, obj):
        return obj.likes.count()


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "is_public", "tracks_count", "updated_at")
    list_filter = ("is_public", "created_at", "updated_at")
    search_fields = ("name", "description", "user__username")
    filter_horizontal = ("tracks",)

    @admin.display(description="ط§ظ„ظ…ظ‚ط§ط·ط¹")
    def tracks_count(self, obj):
        return obj.tracks.count()


@admin.register(ListeningHistory)
class ListeningHistoryAdmin(admin.ModelAdmin):
    list_display = ("track", "user", "session_key", "played_at")
    list_filter = ("played_at",)
    search_fields = ("track__title", "user__username", "session_key")
    autocomplete_fields = ("track", "user")


@admin.register(QueueItem)
class QueueItemAdmin(admin.ModelAdmin):
    list_display = ("user", "track", "created_at")
    search_fields = ("user__username", "track__title")
    autocomplete_fields = ("user", "track")


@admin.register(TrackComment)
class TrackCommentAdmin(admin.ModelAdmin):
    list_display = ("track", "user", "is_visible", "created_at")
    list_filter = ("is_visible", "created_at")
    search_fields = ("track__title", "user__username", "body")
    autocomplete_fields = ("track", "user")
    list_editable = ("is_visible",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "location", "updated_at")
    search_fields = ("user__username", "display_name", "bio", "location", "website")


@admin.register(UserPost)
class UserPostAdmin(admin.ModelAdmin):
    list_display = ("user", "short_body", "shared_track", "likes_total", "is_published", "created_at")
    list_filter = ("is_published", "created_at")
    search_fields = ("user__username", "body")
    autocomplete_fields = ("user", "shared_track")

    @admin.display(description="ط§ظ„ظ†طµ")
    def short_body(self, obj):
        return obj.body[:70]

    @admin.display(description="ط§ظ„ط¥ط¹ط¬ط§ط¨ط§طھ")
    def likes_total(self, obj):
        return obj.likes.count()


@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "short_body", "is_visible", "created_at")
    list_filter = ("is_visible", "created_at")
    search_fields = ("user__username", "body", "post__body")
    autocomplete_fields = ("user", "post")
    list_editable = ("is_visible",)

    @admin.display(description="ط§ظ„طھط¹ظ„ظٹظ‚")
    def short_body(self, obj):
        return obj.body[:70]


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ("ip_address", "reason", "severity", "path", "created_at")
    list_filter = ("severity", "created_at")
    search_fields = ("ip_address", "path", "user_agent", "reason")
    readonly_fields = ("ip_address", "path", "user_agent", "reason", "severity", "created_at")

    def has_add_permission(self, request):
        return False


@admin.register(BlockedIP)
class BlockedIPAdmin(admin.ModelAdmin):
    list_display = ("ip_address", "reason", "expires_at", "is_active", "updated_at")
    list_filter = ("is_active", "updated_at")
    search_fields = ("ip_address", "reason")
    list_editable = ("is_active",)


@admin.register(VisitEvent)
class VisitEventAdmin(admin.ModelAdmin):
    list_display = ("path", "ip_address", "country_code", "status_code", "response_ms", "visited_at")
    list_filter = ("status_code", "country_code", "is_staff_request", "visited_at")
    search_fields = ("path", "ip_address", "referer", "user_agent")
    readonly_fields = (
        "user",
        "path",
        "method",
        "status_code",
        "response_ms",
        "ip_address",
        "country_code",
        "user_agent",
        "referer",
        "is_staff_request",
        "visited_at",
    )

    def has_add_permission(self, request):
        return False

