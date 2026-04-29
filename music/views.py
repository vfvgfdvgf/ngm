import random
from io import BytesIO
from datetime import timedelta
from mimetypes import guess_type
from urllib.parse import urlencode

from django.contrib import admin
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Avg, BooleanField, Count, Exists, F, OuterRef, Prefetch, Q, Value
from django.db.models.functions import TruncDate
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.cache import patch_cache_control
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import (
    ProfileForm,
    QuickAlbumForm,
    QuickAnnouncementForm,
    QuickArtistForm,
    QuickCategoryForm,
    QuickFAQForm,
    QuickLegalPageForm,
    QuickTrackForm,
    SiteBrandingForm,
    SignupForm,
    StaffAccountForm,
    UserPostForm,
)
from .models import (
    Album,
    Announcement,
    Artist,
    Category,
    FAQ,
    LegalPage,
    ListeningHistory,
    PageBanner,
    PAGE_CHOICES,
    Playlist,
    PostComment,
    QueueItem,
    SEOPage,
    SecurityEvent,
    SiteSettings,
    StoredMediaFile,
    Track,
    TrackComment,
    UserPost,
    UserProfile,
    VisitEvent,
    BlockedIP,
)


def get_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def paginate_queryset(request, queryset_or_list, per_page=24, page_param="page"):
    paginator = Paginator(queryset_or_list, per_page)
    page_number = request.GET.get(page_param)
    return paginator.get_page(page_number)


def cached_payload(cache_key, timeout, builder):
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    payload = builder()
    cache.set(cache_key, payload, timeout)
    return payload


def safe_redirect_back(request, fallback_name):
    referer = request.META.get("HTTP_REFERER", "")
    if referer and url_has_allowed_host_and_scheme(
        url=referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(referer)
    return redirect(fallback_name)


def is_staff_user(user):
    return bool(user and user.is_authenticated and user.is_staff)


def _parse_http_range(range_header, total_size):
    if not range_header or not range_header.startswith("bytes="):
        return None

    try:
        range_value = range_header.split("=", 1)[1].split(",", 1)[0].strip()
        if "-" not in range_value:
            return None

        start_str, end_str = range_value.split("-", 1)
        if start_str == "":
            suffix_length = int(end_str)
            if suffix_length <= 0:
                return None
            start = max(total_size - suffix_length, 0)
            end = total_size - 1
        else:
            start = int(start_str)
            end = int(end_str) if end_str else total_size - 1
    except (TypeError, ValueError):
        return None

    if start < 0 or end < start or start >= total_size:
        return None

    return start, min(end, total_size - 1)


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.get_or_create(user=user)
            auth_login(request, user)
            messages.success(request, "تم إنشاء حسابك بنجاح. أهلاً بك في نغم.")
            return redirect("library")
    else:
        form = SignupForm()

    return render(request, "registration/signup.html", {"form": form})


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        auth_logout(request)
        messages.success(request, "تم تسجيل الخروج بنجاح.")
    return redirect("home")


def published_tracks():
    return (
        Track.objects.filter(is_published=True)
        .select_related("artist", "album", "category")
        .annotate(likes_count=Count("likes", distinct=True))
        .prefetch_related("likes", "saved_by")
    )


def random_published_tracks(limit=24):
    track_ids = list(Track.objects.filter(is_published=True).values_list("id", flat=True))
    if len(track_ids) <= limit:
        return list(published_tracks()[:limit])

    sampled_ids = random.sample(track_ids, limit)
    tracks_by_id = {
        track.id: track for track in published_tracks().filter(id__in=sampled_ids)
    }
    return [tracks_by_id[track_id] for track_id in sampled_ids if track_id in tracks_by_id]


def public_playlists(limit=None):
    queryset = (
        Playlist.objects.filter(is_public=True)
        .select_related("user")
        .annotate(tracks_count=Count("tracks", distinct=True))
        .order_by("-tracks_count", "-updated_at")
    )
    return queryset if limit is None else queryset[:limit]


def spotlight_artists(limit=None):
    queryset = (
        Artist.objects.annotate(
            track_count=Count("tracks", distinct=True),
            followers_count=Count("followers", distinct=True),
        )
        .order_by("-followers_count", "-track_count", "name")
    )
    return queryset if limit is None else queryset[:limit]


def latest_albums(limit=None):
    queryset = (
        Album.objects.select_related("artist", "category")
        .annotate(tracks_count=Count("tracks", distinct=True))
        .order_by("-release_date", "-created_at")
    )
    return queryset if limit is None else queryset[:limit]


def recent_community_posts(limit=4, viewer=None):
    return list(community_posts_queryset(viewer=viewer).order_by("-created_at")[:limit])


def build_mood_spotlights(limit=4, tracks_per_mood=3):
    cache_key = f"public:mood-spotlights:{limit}:{tracks_per_mood}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    base_queryset = published_tracks()
    collections = []

    for value, label in Track.MOOD_CHOICES:
        mood_queryset = base_queryset.filter(mood=value).order_by("-views", "-created_at")
        lead_tracks = list(mood_queryset[:tracks_per_mood])
        if not lead_tracks:
            continue
        collections.append(
            {
                "slug": value,
                "label": label,
                "count": mood_queryset.count(),
                "lead": lead_tracks[0],
                "tracks": lead_tracks,
            }
        )

    collections.sort(key=lambda item: (-item["count"], item["label"]))
    payload = collections[:limit]
    cache.set(cache_key, payload, 180)
    return payload


def recent_distinct_tracks(user, limit=6):
    history_items = (
        user.listening_history.select_related("track", "track__artist", "track__album", "track__category")
        .filter(track__is_published=True)
    )
    distinct_tracks = []
    seen_track_ids = set()

    for item in history_items:
        if item.track_id in seen_track_ids:
            continue
        seen_track_ids.add(item.track_id)
        distinct_tracks.append(item.track)
        if len(distinct_tracks) >= limit:
            break

    return distinct_tracks


def build_personal_mix(user, limit=6):
    artist_ids = set(user.followed_artists.values_list("id", flat=True))
    artist_ids.update(user.saved_tracks.values_list("artist_id", flat=True))
    artist_ids.update(user.liked_tracks.values_list("artist_id", flat=True))

    category_ids = set(
        user.saved_tracks.exclude(category__isnull=True).values_list("category_id", flat=True)
    )
    category_ids.update(
        user.liked_tracks.exclude(category__isnull=True).values_list("category_id", flat=True)
    )
    category_ids.update(
        user.listening_history.exclude(track__category__isnull=True).values_list(
            "track__category_id", flat=True
        )[:24]
    )

    if not artist_ids and not category_ids:
        return list(published_tracks().order_by("-is_featured", "-views", "-created_at")[:limit])

    listened_track_ids = list(user.listening_history.values_list("track_id", flat=True)[:30])
    personalized = published_tracks().filter(
        Q(artist_id__in=artist_ids) | Q(category_id__in=category_ids)
    )
    if listened_track_ids:
        personalized = personalized.exclude(id__in=listened_track_ids)

    return list(personalized.order_by("-is_featured", "-views", "-created_at")[:limit])


def duration_bucket_options():
    return [
        ("short", "أقل من 5 دقائق"),
        ("medium", "من 5 إلى 15 دقيقة"),
        ("long", "أكثر من 15 دقيقة"),
    ]


def apply_duration_bucket(queryset, bucket):
    if bucket == "short":
        return queryset.filter(duration_seconds__gt=0, duration_seconds__lt=300)
    if bucket == "medium":
        return queryset.filter(duration_seconds__gte=300, duration_seconds__lte=900)
    if bucket == "long":
        return queryset.filter(duration_seconds__gt=900)
    return queryset


def format_duration_label(total_seconds):
    if not total_seconds:
        return "0:00"
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d}"


def build_search_collections(query, limit=6):
    if not query:
        return {
            "artists": [],
            "albums": [],
            "playlists": [],
            "categories": [],
        }

    artists = list(
        Artist.objects.annotate(
            track_count=Count("tracks", distinct=True),
            followers_count=Count("followers", distinct=True),
        )
        .filter(Q(name__icontains=query) | Q(bio__icontains=query))
        .order_by("-followers_count", "-track_count", "name")[:limit]
    )
    albums = list(
        Album.objects.select_related("artist", "category")
        .annotate(tracks_count=Count("tracks", distinct=True))
        .filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(artist__name__icontains=query)
        )
        .order_by("-release_date", "-created_at")[:limit]
    )
    playlists = list(
        Playlist.objects.filter(is_public=True)
        .select_related("user")
        .annotate(tracks_count=Count("tracks", distinct=True))
        .filter(Q(name__icontains=query) | Q(description__icontains=query))
        .order_by("-tracks_count", "-updated_at")[:limit]
    )
    categories = list(
        Category.objects.annotate(track_count=Count("tracks", distinct=True))
        .filter(Q(name__icontains=query) | Q(description__icontains=query))
        .order_by("-track_count", "name")[:limit]
    )
    return {
        "artists": artists,
        "albums": albums,
        "playlists": playlists,
        "categories": categories,
    }


def build_related_playlists(playlist, limit=4):
    track_ids = list(playlist.tracks.values_list("id", flat=True))
    if not track_ids:
        return []

    return list(
        Playlist.objects.filter(is_public=True)
        .exclude(id=playlist.id)
        .annotate(
            tracks_count=Count("tracks", distinct=True),
            shared_tracks=Count("tracks", filter=Q(tracks__id__in=track_ids), distinct=True),
        )
        .filter(shared_tracks__gt=0)
        .select_related("user")
        .order_by("-shared_tracks", "-tracks_count", "-updated_at")[:limit]
    )


def build_search_archive_urls():
    cached = cache.get("search:archive-urls:v1")
    if cached is not None:
        return cached

    archives = [{"url": reverse("search"), "label": "الاستكشاف"}]

    for mood_value, mood_label in Track.MOOD_CHOICES:
        archives.append(
            {
                "url": f"{reverse('search')}?{urlencode({'mood': mood_value, 'sort': 'popular'})}",
                "label": mood_label,
            }
        )

    for category in Category.objects.order_by("name"):
        archives.append(
            {
                "url": f"{reverse('search')}?{urlencode({'category': category.id, 'sort': 'popular'})}",
                "label": category.name,
            }
        )

    cache.set("search:archive-urls:v1", archives, 600)
    return archives


def build_home_public_payload():
    base_tracks = published_tracks()
    return {
        "tracks": list(base_tracks[:12]),
        "featured_tracks": list(base_tracks.filter(is_featured=True)[:6]),
        "trending_tracks": list(base_tracks.order_by("-views", "-created_at")[:6]),
        "categories": list(Category.objects.annotate(track_count=Count("tracks")).order_by("name")[:8]),
        "artists": list(spotlight_artists(limit=8)),
        "playlists": list(public_playlists(limit=6)),
        "new_albums": list(latest_albums(limit=6)),
        "recent_posts": recent_community_posts(limit=4),
        "mood_spotlights": build_mood_spotlights(limit=4, tracks_per_mood=3),
        "community_stats": {
            "tracks": Track.objects.filter(is_published=True).count(),
            "artists": Artist.objects.count(),
            "playlists": Playlist.objects.filter(is_public=True).count(),
            "members": get_user_model().objects.count(),
        },
    }


def build_discover_public_payload():
    return {
        "tracks": random_published_tracks(limit=24),
        "categories": list(Category.objects.annotate(track_count=Count("tracks"))),
        "mood_spotlights": build_mood_spotlights(limit=5, tracks_per_mood=4),
        "artists": list(spotlight_artists(limit=6)),
        "playlists": list(public_playlists(limit=6)),
        "albums": list(latest_albums(limit=6)),
        "chart_tracks": list(published_tracks().order_by("-views", "-created_at")[:6]),
    }


def build_community_public_payload():
    anonymous_viewer = type("AnonymousViewer", (), {"is_authenticated": False})()
    return {
        "community_tracks": list(published_tracks().order_by("-likes_count", "-views", "-created_at")[:8]),
        "community_playlists": list(public_playlists(limit=6)),
        "community_artists": list(spotlight_artists(limit=8)),
        "trending_categories": list(
            Category.objects.annotate(track_count=Count("tracks")).order_by("-track_count", "name")[:6]
        ),
        "community_stats": {
            "listeners": get_user_model().objects.count(),
            "posts": UserPost.objects.filter(is_published=True).count(),
            "playlists": Playlist.objects.filter(is_public=True).count(),
            "comments": PostComment.objects.filter(is_visible=True).count(),
        },
        "recommended_posts": build_recommended_posts(anonymous_viewer, limit=6),
    }


def community_posts_queryset(viewer=None):
    queryset = (
        UserPost.objects.filter(is_published=True)
        .select_related(
            "user",
            "user__profile",
            "shared_track",
            "shared_track__artist",
            "shared_track__album",
            "shared_track__category",
        )
        .annotate(
            likes_count=Count("likes", distinct=True),
            comments_count=Count("comments", filter=Q(comments__is_visible=True), distinct=True),
        )
        .prefetch_related(
            Prefetch(
                "comments",
                queryset=PostComment.objects.filter(is_visible=True)
                .select_related("user", "user__profile")
                .order_by("-created_at"),
                to_attr="visible_comments",
            )
        )
    )

    if viewer and viewer.is_authenticated:
        likes_through = UserPost.likes.through.objects.filter(
            userpost_id=OuterRef("pk"),
            user_id=viewer.id,
        )
        queryset = queryset.annotate(viewer_has_liked=Exists(likes_through))
    else:
        queryset = queryset.annotate(
            viewer_has_liked=Value(False, output_field=BooleanField())
        )

    return queryset


def build_recommended_posts(user, limit=6):
    if not user.is_authenticated:
        return list(
            community_posts_queryset().order_by("-likes_count", "-comments_count", "-created_at")[:limit]
        )

    followed_artist_ids = list(user.followed_artists.values_list("id", flat=True))
    saved_track_ids = list(user.saved_tracks.values_list("id", flat=True))
    liked_track_ids = list(user.liked_tracks.values_list("id", flat=True))
    engaged_post_user_ids = set(user.liked_posts.values_list("user_id", flat=True))
    engaged_post_user_ids.update(user.post_comments.values_list("post__user_id", flat=True))

    recommended = community_posts_queryset(viewer=user).exclude(user=user).filter(
        Q(shared_track__artist_id__in=followed_artist_ids)
        | Q(shared_track_id__in=saved_track_ids)
        | Q(shared_track_id__in=liked_track_ids)
        | Q(user_id__in=engaged_post_user_ids)
    )

    posts = list(recommended.order_by("-likes_count", "-comments_count", "-created_at")[:limit])
    if len(posts) >= limit:
        return posts

    seen_ids = {post.id for post in posts}
    fallback = community_posts_queryset(viewer=user).exclude(id__in=seen_ids).exclude(user=user).order_by(
        "-likes_count", "-comments_count", "-created_at"
    )[: limit - len(posts)]
    posts.extend(list(fallback))
    return posts


def build_search_page_seo(query, mood, category, duration_bucket):
    category_name = category.name if category else ""
    if query:
        return {
            "title": f"نتائج البحث عن {query}",
            "description": f"استعرض نتائج البحث عن {query} داخل نغم.",
            "noindex": True,
            "canonical": f"{reverse('search')}?{urlencode({'q': query})}",
        }

    if mood or category or duration_bucket:
        parts = []
        if mood:
            parts.append(dict(Track.MOOD_CHOICES).get(mood, mood))
        if category_name:
            parts.append(category_name)
        if duration_bucket:
            parts.append(dict(duration_bucket_options()).get(duration_bucket, duration_bucket))

        params = {}
        if mood:
            params["mood"] = mood
        if category:
            params["category"] = category.id
        if duration_bucket:
            params["duration"] = duration_bucket
        params["sort"] = "popular"

        label = " - ".join(parts) if parts else "المقاطع"
        return {
            "title": f"بحث نغم: {label}",
            "description": f"اكتشف مقاطع {label} داخل نغم مع تصفح منظم وقابل للأرشفة.",
            "noindex": False,
            "canonical": f"{reverse('search')}?{urlencode(params)}",
        }

    return {
        "title": "البحث",
        "description": "ابحث في المقاطع والفنانين والألبومات والقوائم العامة داخل نغم.",
        "noindex": False,
        "canonical": reverse("search"),
    }


def bounded_score(value):
    return max(0, min(100, int(round(value))))


def build_dashboard_health_center(*, avg_response_ms, slow_pages_count, server_errors_week):
    site_settings = SiteSettings.load()
    configured_seo_pages = SEOPage.objects.count()
    expected_seo_pages = len(PAGE_CHOICES)
    missing_seo_pages = max(0, expected_seo_pages - configured_seo_pages)

    published_tracks_total = Track.objects.filter(is_published=True).count()
    tracks_without_cover = Track.objects.filter(is_published=True).filter(
        Q(cover="") | Q(cover__isnull=True)
    ).count()
    artists_without_image = Artist.objects.filter(Q(image="") | Q(image__isnull=True)).count()
    albums_without_cover = Album.objects.filter(Q(cover="") | Q(cover__isnull=True)).count()

    performance_score = 100
    if avg_response_ms > 180:
        performance_score -= min(45, int((avg_response_ms - 180) / 18))
    performance_score -= slow_pages_count * 4
    performance_score -= min(18, server_errors_week * 3)
    performance_score = bounded_score(performance_score)

    seo_score = 100
    if not site_settings.canonical_domain.strip():
        seo_score -= 24
    if not site_settings.og_image:
        seo_score -= 14
    if not site_settings.default_keywords.strip():
        seo_score -= 8
    seo_score -= min(32, missing_seo_pages * 4)
    seo_score = bounded_score(seo_score)

    media_score = 100
    if published_tracks_total:
        media_score -= min(30, int((tracks_without_cover / published_tracks_total) * 40))
    media_score -= min(18, artists_without_image * 2)
    media_score -= min(18, albums_without_cover * 2)
    media_score = bounded_score(media_score)

    next_steps = []
    if avg_response_ms > 220:
        next_steps.append(
            {
                "title": "خفض زمن الاستجابة",
                "detail": f"المتوسط الحالي {avg_response_ms}ms، والأفضل أن يبقى قريبًا من 200ms أو أقل.",
                "tone": "warning",
            }
        )
    if slow_pages_count:
        next_steps.append(
            {
                "title": "معالجة الصفحات الأبطأ",
                "detail": f"هناك {slow_pages_count} صفحات تحتاج تحسين استعلامات أو تبسيط الواجهة.",
                "tone": "warning",
            }
        )
    if missing_seo_pages:
        next_steps.append(
            {
                "title": "إكمال تغطية SEO",
                "detail": f"لا تزال {missing_seo_pages} صفحات بلا إعداد SEO مخصص داخل اللوحة.",
                "tone": "info",
            }
        )
    if not site_settings.canonical_domain.strip():
        next_steps.append(
            {
                "title": "تحديد الدومين القانوني",
                "detail": "إضافة canonical domain سترفع وضوح الأرشفة وتمنع تكرار الروابط.",
                "tone": "info",
            }
        )
    if tracks_without_cover or artists_without_image or albums_without_cover:
        next_steps.append(
            {
                "title": "استكمال الصور الناقصة",
                "detail": f"مقاطع بلا غلاف: {tracks_without_cover}، فنانون بلا صورة: {artists_without_image}، ألبومات بلا غلاف: {albums_without_cover}.",
                "tone": "info",
            }
        )
    if not next_steps:
        next_steps.append(
            {
                "title": "الحالة ممتازة",
                "detail": "لا توجد فجوات كبيرة الآن، ويمكن التركيز على توسيع المحتوى وتحسين التحويلات.",
                "tone": "success",
            }
        )

    return {
        "overall_score": bounded_score((performance_score + seo_score + media_score) / 3),
        "performance_score": performance_score,
        "seo_score": seo_score,
        "media_score": media_score,
        "metrics": {
            "missing_seo_pages": missing_seo_pages,
            "tracks_without_cover": tracks_without_cover,
            "artists_without_image": artists_without_image,
            "albums_without_cover": albums_without_cover,
            "server_errors_week": server_errors_week,
        },
        "next_steps": next_steps[:5],
    }


def build_dashboard_snapshot():
    cache_key = "dashboard:snapshot:v1"
    cached = cache.get(cache_key)
    if cached:
        return cached

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=6)
    month_start = today_start - timedelta(days=29)

    visits = VisitEvent.objects.all()
    visits_today = visits.filter(visited_at__gte=today_start)
    visits_week = visits.filter(visited_at__gte=week_start)
    visits_month = visits.filter(visited_at__gte=month_start)

    trend_rows = (
        visits_month.annotate(day=TruncDate("visited_at"))
        .values("day")
        .annotate(
            visits=Count("id"),
            unique_ips=Count("ip_address", distinct=True),
        )
        .order_by("day")
    )

    top_pages = list(
        visits_week.values("path")
        .annotate(total=Count("id"), avg_ms=Avg("response_ms"))
        .order_by("-total", "path")[:8]
    )
    top_countries = list(
        visits_month.exclude(country_code="")
        .values("country_code")
        .annotate(total=Count("id"))
        .order_by("-total", "country_code")[:8]
    )
    top_ips = list(
        visits_week.values("ip_address")
        .annotate(total=Count("id"))
        .order_by("-total", "ip_address")[:10]
    )
    top_referrers = list(
        visits_week.exclude(referer="")
        .values("referer")
        .annotate(total=Count("id"))
        .order_by("-total", "referer")[:6]
    )
    slow_pages = list(
        visits_week.values("path")
        .annotate(avg_ms=Avg("response_ms"), total=Count("id"))
        .filter(total__gte=3)
        .order_by("-avg_ms", "-total")[:6]
    )
    status_codes = list(
        visits_week.values("status_code")
        .annotate(total=Count("id"))
        .order_by("-total", "status_code")[:6]
    )
    server_errors_week = visits_week.filter(status_code__gte=500).count()

    security_today = SecurityEvent.objects.filter(created_at__gte=today_start)
    security_summary = {
        "today": security_today.count(),
        "high": security_today.filter(severity="high").count(),
        "medium": security_today.filter(severity="medium").count(),
        "active_blocks": BlockedIP.objects.filter(is_active=True, expires_at__gt=now).count(),
    }

    recent_security_events = list(
        SecurityEvent.objects.all().order_by("-created_at")[:10]
    )
    recent_visits = list(
        visits.select_related("user").order_by("-visited_at")[:12]
    )
    trends = list(trend_rows)
    max_visits = max([row["visits"] for row in trends], default=0)
    trend_cards = []
    for row in trends:
        visits_total = row["visits"]
        trend_cards.append(
            {
                "label": row["day"].strftime("%m-%d"),
                "visits": visits_total,
                "unique_ips": row["unique_ips"],
                "height": max(12, int((visits_total / max_visits) * 100)) if max_visits else 0,
            }
        )

    top_country = top_countries[0] if top_countries else None
    top_ip = top_ips[0] if top_ips else None
    top_page = top_pages[0] if top_pages else None
    peak_day = max(trends, key=lambda row: row["visits"], default=None)
    staff_requests_week = visits_week.filter(is_staff_request=True).count()
    avg_response_ms = int((visits_week.aggregate(avg=Avg("response_ms"))["avg"] or 0))
    health_center = build_dashboard_health_center(
        avg_response_ms=avg_response_ms,
        slow_pages_count=len(slow_pages),
        server_errors_week=server_errors_week,
    )

    payload = {
        "overview": {
            "visits_today": visits_today.count(),
            "visits_week": visits_week.count(),
            "visits_month": visits_month.count(),
            "unique_ips_today": visits_today.values("ip_address").distinct().count(),
            "unique_ips_week": visits_week.values("ip_address").distinct().count(),
            "signed_in_visitors": visits_week.exclude(user__isnull=True).values("user_id").distinct().count(),
            "avg_response_ms": avg_response_ms,
            "staff_requests_week": staff_requests_week,
            "top_country": top_country,
            "top_ip": top_ip,
            "top_page": top_page,
            "peak_day": {
                "label": peak_day["day"].strftime("%Y-%m-%d"),
                "visits": peak_day["visits"],
            }
            if peak_day
            else None,
        },
        "content": {
            "tracks": Track.objects.filter(is_published=True).count(),
            "artists": Artist.objects.count(),
            "albums": Album.objects.count(),
            "playlists": Playlist.objects.count(),
            "users": get_user_model().objects.count(),
            "posts": UserPost.objects.filter(is_published=True).count(),
            "track_comments": TrackComment.objects.filter(is_visible=True).count(),
            "post_comments": PostComment.objects.filter(is_visible=True).count(),
            "plays_week": ListeningHistory.objects.filter(played_at__gte=week_start).count(),
        },
        "trends": trends,
        "trend_cards": trend_cards,
        "top_pages": top_pages,
        "top_countries": top_countries,
        "top_ips": top_ips,
        "top_referrers": top_referrers,
        "slow_pages": slow_pages,
        "status_codes": status_codes,
        "server_errors_week": server_errors_week,
        "security_summary": security_summary,
        "health_center": health_center,
        "recent_security_events": recent_security_events,
        "recent_visits": recent_visits,
    }
    cache.set(cache_key, payload, 60)
    return payload


def build_dashboard_content_snapshot():
    cache_key = "dashboard:content:v1"
    cached = cache.get(cache_key)
    if cached:
        return cached

    top_tracks = list(
        Track.objects.filter(is_published=True)
        .select_related("artist", "album")
        .annotate(likes_total=Count("likes", distinct=True), comments_total=Count("comments", distinct=True))
        .order_by("-views", "-likes_total", "-created_at")[:8]
    )
    top_artists = list(
        Artist.objects.annotate(
            followers_total=Count("followers", distinct=True),
            tracks_total=Count("tracks", distinct=True),
        ).order_by("-followers_total", "-tracks_total", "name")[:8]
    )
    latest_posts = list(
        UserPost.objects.filter(is_published=True)
        .select_related("user", "shared_track", "shared_track__artist")
        .annotate(likes_total=Count("likes", distinct=True), comments_total=Count("comments", distinct=True))
        .order_by("-created_at")[:8]
    )
    latest_playlists = list(
        Playlist.objects.select_related("user")
        .annotate(tracks_total=Count("tracks", distinct=True))
        .order_by("-updated_at")[:8]
    )

    payload = {
        "top_tracks": top_tracks,
        "top_artists": top_artists,
        "latest_posts": latest_posts,
        "latest_playlists": latest_playlists,
    }
    cache.set(cache_key, payload, 120)
    return payload


def build_dashboard_security_snapshot():
    cache_key = "dashboard:security:v1"
    cached = cache.get(cache_key)
    if cached:
        return cached

    now = timezone.now()
    recent_events = list(SecurityEvent.objects.order_by("-created_at")[:20])
    active_blocks = list(BlockedIP.objects.filter(is_active=True, expires_at__gt=now).order_by("-updated_at")[:20])
    top_attackers = list(
        SecurityEvent.objects.values("ip_address")
        .annotate(total=Count("id"))
        .order_by("-total", "ip_address")[:10]
    )
    common_paths = list(
        SecurityEvent.objects.values("path")
        .annotate(total=Count("id"))
        .order_by("-total", "path")[:10]
    )
    severity_breakdown = list(
        SecurityEvent.objects.values("severity")
        .annotate(total=Count("id"))
        .order_by("-total", "severity")
    )

    payload = {
        "recent_events": recent_events,
        "active_blocks": active_blocks,
        "top_attackers": top_attackers,
        "common_paths": common_paths,
        "severity_breakdown": severity_breakdown,
    }
    cache.set(cache_key, payload, 60)
    return payload


def build_dashboard_users_snapshot():
    cache_key = "dashboard:users:v1"
    cached = cache.get(cache_key)
    if cached:
        return cached

    user_model = get_user_model()
    now = timezone.now()
    month_start = now - timedelta(days=30)

    recent_users = list(
        user_model.objects.select_related("profile").order_by("-date_joined")[:12]
    )
    top_profiles = list(
        UserProfile.objects.select_related("user")
        .annotate(posts_total=Count("user__posts", distinct=True), comments_total=Count("user__track_comments", distinct=True))
        .order_by("-posts_total", "-comments_total", "user__username")[:10]
    )
    staff_users = list(
        user_model.objects.filter(is_staff=True).order_by("-last_login", "username")[:10]
    )

    payload = {
        "totals": {
            "all_users": user_model.objects.count(),
            "new_users_month": user_model.objects.filter(date_joined__gte=month_start).count(),
            "staff_users": user_model.objects.filter(is_staff=True).count(),
            "superusers": user_model.objects.filter(is_superuser=True).count(),
            "profiles_completed": UserProfile.objects.exclude(display_name="").count(),
        },
        "recent_users": recent_users,
        "top_profiles": top_profiles,
        "staff_users": staff_users,
    }
    cache.set(cache_key, payload, 120)
    return payload


def build_dashboard_reports_snapshot():
    cache_key = "dashboard:reports:v1"
    cached = cache.get(cache_key)
    if cached:
        return cached

    user_model = get_user_model()
    now = timezone.now()
    month_start = now - timedelta(days=29)

    signup_trends = list(
        user_model.objects.filter(date_joined__gte=month_start)
        .annotate(day=TruncDate("date_joined"))
        .values("day")
        .annotate(total=Count("id"))
        .order_by("day")
    )
    max_signups = max([row["total"] for row in signup_trends], default=0)
    signup_cards = [
        {
            "label": row["day"].strftime("%m-%d"),
            "total": row["total"],
            "height": max(12, int((row["total"] / max_signups) * 100)) if max_signups else 0,
        }
        for row in signup_trends
    ]
    publishing = {
        "tracks_month": Track.objects.filter(created_at__gte=month_start).count(),
        "albums_month": Album.objects.filter(created_at__gte=month_start).count(),
        "playlists_month": Playlist.objects.filter(created_at__gte=month_start).count(),
        "posts_month": UserPost.objects.filter(created_at__gte=month_start).count(),
        "comments_month": (
            TrackComment.objects.filter(created_at__gte=month_start).count()
            + PostComment.objects.filter(created_at__gte=month_start).count()
        ),
    }

    payload = {
        "signup_trends": signup_trends,
        "signup_cards": signup_cards,
        "publishing": publishing,
        "engagement": {
            "listens_month": ListeningHistory.objects.filter(played_at__gte=month_start).count(),
            "likes_tracks": Track.likes.through.objects.count(),
            "likes_posts": UserPost.likes.through.objects.count(),
            "saved_tracks": Track.saved_by.through.objects.count(),
            "queue_items": QueueItem.objects.count(),
        },
    }
    cache.set(cache_key, payload, 120)
    return payload


def build_dashboard_seo_snapshot():
    cache_key = "dashboard:seo:v1"
    cached = cache.get(cache_key)
    if cached:
        return cached

    seo_pages = list(SEOPage.objects.order_by("page_key"))
    banner_pages = list(PageBanner.objects.order_by("page_key", "sort_order", "id"))
    legal_recent = list(LegalPage.objects.order_by("-updated_at")[:10])
    announcements = list(Announcement.objects.order_by("-created_at")[:8])
    site_settings = SiteSettings.load()
    configured_pages = {page.page_key for page in seo_pages}
    missing_pages = [
        {"key": key, "label": label}
        for key, label in PAGE_CHOICES
        if key not in configured_pages
    ]

    payload = {
        "site_settings": site_settings,
        "seo_pages": seo_pages,
        "banner_pages": banner_pages,
        "legal_recent": legal_recent,
        "announcements": announcements,
        "missing_pages": missing_pages,
        "health_checks": [
            {
                "label": "الدومين القانوني",
                "status": "ready" if site_settings.canonical_domain.strip() else "missing",
                "detail": site_settings.canonical_domain or "غير محدد",
            },
            {
                "label": "صورة Open Graph",
                "status": "ready" if site_settings.og_image else "missing",
                "detail": "موجودة" if site_settings.og_image else "غير مرفوعة",
            },
            {
                "label": "تغطية صفحات SEO",
                "status": "ready" if not missing_pages else "warning",
                "detail": f"{len(seo_pages)} من {len(PAGE_CHOICES)} صفحة",
            },
            {
                "label": "sitemap و robots",
                "status": "ready",
                "detail": "مفعلة داخل المشروع",
            },
        ],
        "opportunities": [
            {
                "title": "إكمال الصفحات الناقصة",
                "detail": f"{len(missing_pages)} صفحات لا تزال بلا SEO مخصص.",
            }
            if missing_pages
            else {
                "title": "تغطية SEO مكتملة",
                "detail": "كل الصفحات المعرفة تملك إعداد SEO مخصص.",
            },
            {
                "title": "رفع صورة OG رئيسية",
                "detail": "إضافة صورة اجتماعية موحدة تحسن المشاركة في واتساب ومنصات التواصل.",
            }
            if not site_settings.og_image
            else {
                "title": "صورة المشاركة جاهزة",
                "detail": "الصورة الاجتماعية الرئيسية متوفرة حاليًا.",
            },
            {
                "title": "ضبط canonical domain",
                "detail": "وجود دومين قانوني ثابت يحسن توحيد الأرشفة بين الروابط.",
            }
            if not site_settings.canonical_domain.strip()
            else {
                "title": "الدومين القانوني مضبوط",
                "detail": site_settings.canonical_domain,
            },
        ],
        "counts": {
            "seo_pages": len(seo_pages),
            "noindex_pages": SEOPage.objects.filter(noindex=True).count(),
            "banners": len(banner_pages),
            "legal_pages": LegalPage.objects.count(),
            "announcements": Announcement.objects.count(),
        },
    }
    cache.set(cache_key, payload, 180)
    return payload


def build_dashboard_media_snapshot():
    cache_key = "dashboard:media:v1"
    cached = cache.get(cache_key)
    if cached:
        return cached

    payload = {
        "coverage": {
            "tracks_with_cover": Track.objects.exclude(cover="").count(),
            "tracks_without_cover": Track.objects.filter(Q(cover="") | Q(cover__isnull=True)).count(),
            "albums_with_cover": Album.objects.exclude(cover="").count(),
            "artists_with_image": Artist.objects.exclude(image="").count(),
            "playlists_with_cover": Playlist.objects.exclude(cover="").count(),
            "profiles_with_avatar": UserProfile.objects.exclude(avatar="").count(),
            "profiles_with_banner": UserProfile.objects.exclude(banner_image="").count(),
            "banners_with_media": PageBanner.objects.exclude(Q(image="") & Q(image_url="")).count(),
        },
        "latest_tracks": list(
            Track.objects.select_related("artist", "album").order_by("-created_at")[:10]
        ),
        "latest_albums": list(
            Album.objects.select_related("artist").order_by("-created_at")[:10]
        ),
        "latest_profiles": list(
            UserProfile.objects.select_related("user").order_by("-updated_at")[:10]
        ),
    }
    cache.set(cache_key, payload, 120)
    return payload


def build_dashboard_settings_snapshot():
    cache_key = "dashboard:settings:v2"
    cached = cache.get(cache_key)
    if cached:
        return cached

    site_settings = SiteSettings.load()
    payload = {
        "site_settings": site_settings,
        "health": {
            "analytics_connected": bool(site_settings.analytics_code.strip()),
            "canonical_domain": site_settings.canonical_domain or "غير محدد",
            "maintenance_message": site_settings.maintenance_message or "لا توجد رسالة صيانة",
            "og_image_ready": bool(site_settings.og_image),
            "logo_ready": bool(site_settings.logo),
            "favicon_ready": bool(site_settings.favicon),
            "branding_admin_url": reverse("staff_dashboard_branding"),
            "header_cta_label": site_settings.header_cta_label,
            "header_cta_url": site_settings.header_cta_url,
        },
        "counts": {
            "seo_pages": SEOPage.objects.count(),
            "banners": PageBanner.objects.count(),
            "legal_pages": LegalPage.objects.count(),
            "faqs": FAQ.objects.count(),
            "announcements": Announcement.objects.count(),
        },
    }
    cache.set(cache_key, payload, 180)
    return payload


def build_admin_model_catalog():
    groups = []
    for model, model_admin in admin.site._registry.items():
        opts = model._meta
        groups.append(
            {
                "app_label": opts.app_label,
                "model_name": opts.model_name,
                "label": opts.verbose_name_plural.title(),
                "add_url": reverse(f"admin:{opts.app_label}_{opts.model_name}_add"),
                "list_url": reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist"),
            }
        )
    return sorted(groups, key=lambda item: (item["app_label"], item["label"]))


def staff_manage_links():
    return [
        {"label": "المقاطع", "url": reverse("admin:music_track_changelist"), "icon": "fa-music"},
        {"label": "الفنانون", "url": reverse("admin:music_artist_changelist"), "icon": "fa-microphone-lines"},
        {"label": "الألبومات", "url": reverse("admin:music_album_changelist"), "icon": "fa-compact-disc"},
        {"label": "القوائم", "url": reverse("admin:music_playlist_changelist"), "icon": "fa-list"},
        {"label": "المستخدمون", "url": reverse("admin:auth_user_changelist"), "icon": "fa-users"},
        {"label": "الحماية", "url": reverse("admin:music_securityevent_changelist"), "icon": "fa-shield-halved"},
        {"label": "الزيارات", "url": reverse("admin:music_visitevent_changelist"), "icon": "fa-chart-simple"},
        {"label": "الصفحات القانونية", "url": reverse("admin:music_legalpage_changelist"), "icon": "fa-scale-balanced"},
    ]


def dashboard_sections(active):
    return [
        {"label": "لوحة القيادة", "url": reverse("staff_dashboard"), "icon": "fa-chart-pie", "active": active == "overview"},
        {"label": "الزوار والتحليلات", "url": reverse("staff_dashboard_visitors"), "icon": "fa-earth-asia", "active": active == "visitors"},
        {"label": "المحتوى والنشر", "url": reverse("staff_dashboard_content"), "icon": "fa-photo-film", "active": active == "content"},
        {"label": "الحماية والمراقبة", "url": reverse("staff_dashboard_security"), "icon": "fa-user-shield", "active": active == "security"},
        {"label": "المستخدمون", "url": reverse("staff_dashboard_users"), "icon": "fa-user-group", "active": active == "users"},
        {"label": "التقارير", "url": reverse("staff_dashboard_reports"), "icon": "fa-file-lines", "active": active == "reports"},
        {"label": "SEO", "url": reverse("staff_dashboard_seo"), "icon": "fa-magnifying-glass-chart", "active": active == "seo"},
        {"label": "الوسائط", "url": reverse("staff_dashboard_media"), "icon": "fa-images", "active": active == "media"},
        {"label": "الإعدادات", "url": reverse("staff_dashboard_settings"), "icon": "fa-sliders", "active": active == "settings"},
        {"label": "إدارة الفريق", "url": reverse("staff_dashboard_team"), "icon": "fa-user-gear", "active": active == "team"},
        {"label": "استوديو النشر", "url": reverse("staff_dashboard_studio"), "icon": "fa-square-plus", "active": active == "studio"},
        {"label": "فهرس الإدارة", "url": reverse("staff_dashboard_admin_index"), "icon": "fa-table-cells-large", "active": active == "admin_index"},
    ]


def build_dashboard_context(active, **extra):
    context = {
        "manage_links": staff_manage_links(),
        "dashboard_sections": dashboard_sections(active),
        "page_title": "لوحة التحكم",
        "page_description": "لوحة عربية حديثة لإدارة نغم ومراقبة الأداء والزيارات والحماية.",
        "page_noindex": True,
        "page_canonical": extra.pop("page_canonical", reverse("staff_dashboard")),
    }
    context.update(extra)
    return context


@login_required
def staff_dashboard(request):
    if not is_staff_user(request.user):
        messages.error(request, "??? ?????? ????? ??????? ????????? ???.")
        return redirect("home")

    return render(
        request,
        "dashboard/index.html",
        build_dashboard_context(
            "overview",
            dashboard=build_dashboard_snapshot(),
            page_canonical=reverse("staff_dashboard"),
        ),
    )


@login_required
def staff_dashboard_visitors(request):
    if not is_staff_user(request.user):
        messages.error(request, "??? ?????? ????? ??????? ????????? ???.")
        return redirect("home")

    return render(
        request,
        "dashboard/visitors.html",
        build_dashboard_context(
            "visitors",
            dashboard=build_dashboard_snapshot(),
            page_canonical=reverse("staff_dashboard_visitors"),
        ),
    )


@login_required
def staff_dashboard_content(request):
    if not is_staff_user(request.user):
        messages.error(request, "??? ?????? ????? ??????? ????????? ???.")
        return redirect("home")

    return render(
        request,
        "dashboard/content.html",
        build_dashboard_context(
            "content",
            dashboard=build_dashboard_snapshot(),
            content_dashboard=build_dashboard_content_snapshot(),
            page_canonical=reverse("staff_dashboard_content"),
        ),
    )


@login_required
def staff_dashboard_security(request):
    if not is_staff_user(request.user):
        messages.error(request, "??? ?????? ????? ??????? ????????? ???.")
        return redirect("home")

    return render(
        request,
        "dashboard/security.html",
        build_dashboard_context(
            "security",
            dashboard=build_dashboard_snapshot(),
            security_dashboard=build_dashboard_security_snapshot(),
            page_canonical=reverse("staff_dashboard_security"),
        ),
    )

@login_required
def staff_dashboard_users(request):
    if not is_staff_user(request.user):
        messages.error(request, "??? ?????? ????? ??????? ????????? ???.")
        return redirect("home")

    return render(
        request,
        "dashboard/users.html",
        build_dashboard_context(
            "users",
            dashboard=build_dashboard_snapshot(),
            users_dashboard=build_dashboard_users_snapshot(),
            page_canonical=reverse("staff_dashboard_users"),
        ),
    )


@login_required
def staff_dashboard_reports(request):
    if not is_staff_user(request.user):
        messages.error(request, "??? ?????? ????? ??????? ????????? ???.")
        return redirect("home")

    return render(
        request,
        "dashboard/reports.html",
        build_dashboard_context(
            "reports",
            dashboard=build_dashboard_snapshot(),
            reports_dashboard=build_dashboard_reports_snapshot(),
            page_canonical=reverse("staff_dashboard_reports"),
        ),
    )


@login_required
def staff_dashboard_seo(request):
    if not is_staff_user(request.user):
        messages.error(request, "??? ?????? ????? ??????? ????????? ???.")
        return redirect("home")

    return render(
        request,
        "dashboard/seo.html",
        build_dashboard_context(
            "seo",
            dashboard=build_dashboard_snapshot(),
            seo_dashboard=build_dashboard_seo_snapshot(),
            page_canonical=reverse("staff_dashboard_seo"),
        ),
    )


@login_required
def staff_dashboard_media(request):
    if not is_staff_user(request.user):
        messages.error(request, "??? ?????? ????? ??????? ????????? ???.")
        return redirect("home")

    return render(
        request,
        "dashboard/media.html",
        build_dashboard_context(
            "media",
            dashboard=build_dashboard_snapshot(),
            media_dashboard=build_dashboard_media_snapshot(),
            page_canonical=reverse("staff_dashboard_media"),
        ),
    )


@login_required
def staff_dashboard_settings(request):
    if not is_staff_user(request.user):
        messages.error(request, "??? ?????? ????? ??????? ????????? ???.")
        return redirect("home")

    return render(
        request,
        "dashboard/settings.html",
        build_dashboard_context(
            "settings",
            dashboard=build_dashboard_snapshot(),
            settings_dashboard=build_dashboard_settings_snapshot(),
            page_canonical=reverse("staff_dashboard_settings"),
        ),
    )


@login_required
def staff_dashboard_branding(request):
    if not is_staff_user(request.user):
        messages.error(request, "??? ?????? ????? ??????? ????????? ???.")
        return redirect("home")

    site_settings = SiteSettings.load()
    form = SiteBrandingForm(request.POST or None, request.FILES or None, instance=site_settings)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم تحديث هوية المنصة بنجاح.")
        return redirect("staff_dashboard_branding")

    return render(
        request,
        "dashboard/branding.html",
        build_dashboard_context(
            "settings",
            dashboard=build_dashboard_snapshot(),
            settings_dashboard=build_dashboard_settings_snapshot(),
            branding_form=form,
            branding_settings=site_settings,
            page_title="هوية المنصة",
            page_canonical=reverse("staff_dashboard_branding"),
        ),
    )

@login_required
def staff_dashboard_team(request):
    if not is_staff_user(request.user):
        messages.error(request, "??? ?????? ????? ??????? ????????? ???.")
        return redirect("home")

    form = StaffAccountForm(request.POST or None)
    if request.method == "POST":
        if not request.user.is_superuser:
            messages.error(request, "????? ?????? ????? ?????? ?????? ???.")
            return redirect("staff_dashboard_team")
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data.get("email", "")
            user.is_staff = True
            user.is_superuser = bool(form.cleaned_data.get("is_superuser"))
            user.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.display_name = form.cleaned_data.get("display_name", "")
            profile.bio = form.cleaned_data.get("bio", "")
            profile.save()
            messages.success(request, f"?? ????? ???? ?????? {user.username}.")
            return redirect("staff_dashboard_team")

    return render(
        request,
        "dashboard/team.html",
        build_dashboard_context(
            "team",
            dashboard=build_dashboard_snapshot(),
            users_dashboard=build_dashboard_users_snapshot(),
            staff_form=form,
            page_canonical=reverse("staff_dashboard_team"),
        ),
    )


@login_required
def staff_dashboard_studio(request):
    if not is_staff_user(request.user):
        messages.error(request, "??? ?????? ????? ??????? ????????? ???.")
        return redirect("home")

    forms_map = {
        "category": QuickCategoryForm,
        "artist": QuickArtistForm,
        "album": QuickAlbumForm,
        "track": QuickTrackForm,
        "announcement": QuickAnnouncementForm,
        "faq": QuickFAQForm,
        "legal": QuickLegalPageForm,
    }
    active_form = request.POST.get("dashboard_form") if request.method == "POST" else ""
    studio_forms = {}
    for key, form_class in forms_map.items():
        if request.method == "POST" and active_form == key:
            studio_forms[key] = form_class(request.POST, request.FILES, prefix=key)
        else:
            studio_forms[key] = form_class(prefix=key)

    if request.method == "POST" and active_form in studio_forms:
        form = studio_forms[active_form]
        if form.is_valid():
            obj = form.save()
            messages.success(request, f"?? ??? {obj} ?????.")
            return redirect("staff_dashboard_studio")

    return render(
        request,
        "dashboard/studio.html",
        build_dashboard_context(
            "studio",
            dashboard=build_dashboard_snapshot(),
            studio_forms=studio_forms,
            page_canonical=reverse("staff_dashboard_studio"),
        ),
    )


@login_required
def staff_dashboard_admin_index(request):
    if not is_staff_user(request.user):
        messages.error(request, "??? ?????? ????? ??????? ????????? ???.")
        return redirect("home")

    return render(
        request,
        "dashboard/admin_index.html",
        build_dashboard_context(
            "admin_index",
            dashboard=build_dashboard_snapshot(),
            admin_catalog=build_admin_model_catalog(),
            page_canonical=reverse("staff_dashboard_admin_index"),
        ),
    )

def home(request):
    public_payload = cached_payload("page:home:public:v2", 180, build_home_public_payload)
    continue_listening = []
    personal_mix = []

    if request.user.is_authenticated:
        continue_listening = recent_distinct_tracks(request.user, limit=4)
        personal_mix = build_personal_mix(request.user, limit=6)

    response = render(
        request,
        "home.html",
        {
            **public_payload,
            "continue_listening": continue_listening,
            "personal_mix": personal_mix,
        },
    )
    if not request.user.is_authenticated:
        patch_cache_control(response, public=True, max_age=120, stale_while_revalidate=120)
    return response


def legal_pages(request):
    pages = LegalPage.objects.filter(is_published=True)
    faqs = FAQ.objects.filter(is_active=True)[:12]
    return render(request, "legal_pages.html", {"pages": pages, "faqs": faqs})


def legal_page_detail(request, slug):
    page = get_object_or_404(LegalPage, slug=slug, is_published=True)
    return render(
        request,
        "legal_page.html",
        {
            "page": page,
            "page_title": page.meta_title or page.title,
            "page_description": page.meta_description or page.summary,
        },
    )


def robots_txt(request):
    response = render(request, "robots.txt", content_type="text/plain")
    patch_cache_control(response, public=True, max_age=3600, stale_while_revalidate=86400)
    return response


def manifest_webmanifest(request):
    site_settings = SiteSettings.load()
    manifest_icons = []
    if site_settings.favicon:
        manifest_icons.append(
            {
                "src": site_settings.favicon.url,
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any",
            }
        )
    elif site_settings.logo:
        manifest_icons.append(
            {
                "src": site_settings.logo.url,
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any",
            }
        )
    payload = {
        "name": site_settings.site_name,
        "short_name": site_settings.site_name[:24],
        "description": site_settings.default_description,
        "lang": "ar",
        "dir": "rtl",
        "start_url": reverse("home"),
        "scope": "/",
        "display": "standalone",
        "background_color": "#f4ebdf",
        "theme_color": "#0f172a",
        "icons": manifest_icons,
    }
    response = JsonResponse(
        payload,
        json_dumps_params={"ensure_ascii": False},
        content_type="application/manifest+json",
    )
    patch_cache_control(response, public=True, max_age=3600, stale_while_revalidate=86400)
    return response


def sitemap_xml(request):
    tracks = published_tracks()
    artists_list = Artist.objects.all()
    albums_list = Album.objects.all()
    legal = LegalPage.objects.filter(is_published=True)
    search_archives = build_search_archive_urls()
    track_comments = TrackComment.objects.filter(is_visible=True).select_related("track")
    post_comments = PostComment.objects.filter(is_visible=True).select_related("post")
    response = render(
        request,
        "sitemap.xml",
        {
            "tracks": tracks,
            "artists": artists_list,
            "albums": albums_list,
            "legal_pages": legal,
            "search_archives": search_archives,
            "track_comments": track_comments,
            "post_comments": post_comments,
        },
        content_type="application/xml",
    )
    patch_cache_control(response, public=True, max_age=1800, stale_while_revalidate=86400)
    return response


def track_detail(request, track_id):
    track = get_object_or_404(published_tracks(), id=track_id)

    suggested_tracks = (
        published_tracks()
        .filter(Q(artist=track.artist) | Q(category=track.category))
        .exclude(id=track.id)
        .order_by("-views", "-created_at")[:8]
    )
    user_playlists = (
        request.user.playlists.all() if request.user.is_authenticated else Playlist.objects.none()
    )
    comments = track.comments.filter(is_visible=True).select_related("user", "user__profile")[:20]

    return render(
        request,
        "track.html",
        {
            "track": track,
            "suggested_tracks": suggested_tracks,
            "user_playlists": user_playlists,
            "comments": comments,
            "play_ping_url": f"/track/{track.id}/play/",
            "page_title": f"{track.title} - {track.artist.name}",
            "page_description": track.description or f"استمع إلى {track.title} بصوت {track.artist.name} على نغم.",
            "page_image": track.cover.url if track.cover else "",
            "page_canonical": reverse("track_detail", args=[track.id]),
        },
    )


def track_comment_detail(request, comment_id):
    comment = get_object_or_404(
        TrackComment.objects.filter(is_visible=True).select_related(
            "track",
            "track__artist",
            "track__album",
            "user",
            "user__profile",
        ),
        id=comment_id,
    )
    return render(
        request,
        "comment_detail.html",
        {
            "comment": comment,
            "comment_kind": "track",
            "comment_target_title": comment.track.title,
            "comment_target_url": reverse("track_detail", args=[comment.track_id]),
            "page_title": f"تعليق على {comment.track.title}",
            "page_description": comment.body[:150],
            "page_image": comment.track.cover.url if comment.track.cover else "",
            "page_canonical": reverse("track_comment_detail", args=[comment.id]),
        },
    )


def post_comment_detail(request, comment_id):
    comment = get_object_or_404(
        PostComment.objects.filter(is_visible=True).select_related(
            "post",
            "post__user",
            "post__user__profile",
            "post__shared_track",
            "post__shared_track__artist",
            "user",
            "user__profile",
        ),
        id=comment_id,
    )
    target_url = reverse("profile_detail", args=[comment.post.user.username])
    target_title = comment.post.shared_track.title if comment.post.shared_track else f"منشور {comment.post.user.username}"
    target_image = ""
    if comment.post.image:
        target_image = comment.post.image.url
    elif comment.post.shared_track and comment.post.shared_track.cover:
        target_image = comment.post.shared_track.cover.url

    return render(
        request,
        "comment_detail.html",
        {
            "comment": comment,
            "comment_kind": "post",
            "comment_target_title": target_title,
            "comment_target_url": target_url,
            "comment_post": comment.post,
            "page_title": f"تعليق في المجتمع - {comment.post.user.username}",
            "page_description": comment.body[:150],
            "page_image": target_image,
            "page_canonical": reverse("post_comment_detail", args=[comment.id]),
        },
    )


def media_file(request, file_key):
    stored = get_object_or_404(StoredMediaFile, file_key=file_key)
    content_type = stored.content_type or guess_type(stored.original_name or stored.file_key)[0] or "application/octet-stream"
    total_size = stored.size or len(stored.content)
    range_header = request.headers.get("Range") or request.META.get("HTTP_RANGE", "")
    byte_range = _parse_http_range(range_header, total_size)

    if byte_range:
        start, end = byte_range
        chunk = bytes(stored.content[start : end + 1])
        response = HttpResponse(chunk, status=206, content_type=content_type)
        response["Content-Range"] = f"bytes {start}-{end}/{total_size}"
        response["Content-Length"] = str(len(chunk))
    else:
        response = FileResponse(BytesIO(bytes(stored.content)), content_type=content_type)
        response["Content-Length"] = str(total_size)

    response["Accept-Ranges"] = "bytes"
    response["Cache-Control"] = "public, max-age=31536000, immutable"
    return response


def site_verification_file(request, verification_filename):
    site_settings = SiteSettings.load()
    if (
        not site_settings.verification_file_name
        or site_settings.verification_file_name.strip() != verification_filename
        or not site_settings.verification_file_content.strip()
    ):
        raise Http404("Verification file not configured.")

    response = HttpResponse(site_settings.verification_file_content, content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "public, max-age=300"
    return response


@require_POST
def register_track_play(request, track_id):
    track = get_object_or_404(Track, id=track_id, is_published=True)
    if not request.session.session_key:
        request.session.create()

    session_key = request.session.session_key or ""
    now = timezone.now()
    recent_cutoff = now - timedelta(minutes=30)

    history_filter = ListeningHistory.objects.filter(track=track, played_at__gte=recent_cutoff)
    if request.user.is_authenticated:
        history_filter = history_filter.filter(user=request.user)
    else:
        history_filter = history_filter.filter(session_key=session_key)

    if history_filter.exists():
        return JsonResponse({"counted": False, "views": track.views})

    ListeningHistory.objects.create(
        user=request.user if request.user.is_authenticated else None,
        track=track,
        session_key=session_key,
    )
    Track.objects.filter(id=track.id).update(views=F("views") + 1)
    track.refresh_from_db(fields=["views"])
    return JsonResponse({"counted": True, "views": track.views})


@require_POST
@login_required
def add_comment(request, track_id):
    track = get_object_or_404(Track, id=track_id, is_published=True)
    body = (request.POST.get("body") or "").strip()
    if not body:
        messages.error(request, "اكتب تعليقًا قبل الإرسال.")
        return redirect("track_detail", track_id=track.id)
    TrackComment.objects.create(track=track, user=request.user, body=body[:600])
    messages.success(request, "تم نشر تعليقك.")
    return redirect("track_detail", track_id=track.id)


@require_POST
def like_track(request, track_id):
    track = get_object_or_404(Track, id=track_id, is_published=True)
    if not request.user.is_authenticated:
        messages.info(request, "سجل الدخول أولًا لتضيف المقاطع إلى المفضلة.")
        return redirect("login")

    if track.likes.filter(id=request.user.id).exists():
        track.likes.remove(request.user)
        messages.success(request, "تمت إزالة المقطع من المفضلة.")
    else:
        track.likes.add(request.user)
        messages.success(request, "تمت إضافة المقطع إلى المفضلة.")

    return safe_redirect_back(request, "home")


@require_POST
@login_required
def save_track(request, track_id):
    track = get_object_or_404(Track, id=track_id, is_published=True)
    if track.saved_by.filter(id=request.user.id).exists():
        track.saved_by.remove(request.user)
        messages.success(request, "تمت إزالة المقطع من مكتبتك.")
    else:
        track.saved_by.add(request.user)
        messages.success(request, "تم حفظ المقطع في مكتبتك.")
    return safe_redirect_back(request, "library")


@require_POST
@login_required
def add_to_queue(request, track_id):
    track = get_object_or_404(Track, id=track_id, is_published=True)
    QueueItem.objects.get_or_create(user=request.user, track=track)
    messages.success(request, "أضيف المقطع إلى قائمة التشغيل التالية.")
    return safe_redirect_back(request, "home")


@require_POST
@login_required
def add_to_playlist(request, track_id):
    track = get_object_or_404(Track, id=track_id, is_published=True)
    playlist_id = request.POST.get("playlist")
    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
    playlist.tracks.add(track)
    messages.success(request, f"أضيف المقطع إلى قائمة {playlist.name}.")
    return safe_redirect_back(request, "home")


def favorites(request):
    tracks = (
        published_tracks().filter(likes=request.user)
        if request.user.is_authenticated
        else []
    )
    return render(
        request,
        "favorites.html",
        {
            "tracks": tracks,
            "page_title": "المفضلة",
            "page_description": "كل المقاطع التي أعجبتك في مكان واحد.",
        },
    )


def library(request):
    saved_query = (request.GET.get("saved_q") or "").strip()
    saved_mood = request.GET.get("saved_mood") or ""
    saved_sort = request.GET.get("saved_sort") or "recent"
    saved_tracks = []
    playlists = (
        request.user.playlists.annotate(tracks_count=Count("tracks", distinct=True))
        if request.user.is_authenticated
        else []
    )
    history = (
        request.user.listening_history.select_related(
            "track", "track__artist", "track__album", "track__category"
        )[:10]
        if request.user.is_authenticated
        else []
    )
    queue = (
        request.user.queue_items.select_related(
            "track", "track__artist", "track__album", "track__category"
        )[:20]
        if request.user.is_authenticated
        else []
    )
    user_profile = get_profile(request.user) if request.user.is_authenticated else None
    post_form = UserPostForm() if request.user.is_authenticated else None
    library_stats = {}
    continue_listening = []
    for_you_tracks = []
    saved_tracks_count = 0
    queue_duration_seconds = 0

    if request.user.is_authenticated:
        saved_tracks_queryset = published_tracks().filter(saved_by=request.user)
        if saved_query:
            saved_tracks_queryset = saved_tracks_queryset.filter(
                Q(title__icontains=saved_query)
                | Q(artist__name__icontains=saved_query)
                | Q(album__title__icontains=saved_query)
            )
        if saved_mood:
            saved_tracks_queryset = saved_tracks_queryset.filter(mood=saved_mood)

        if saved_sort == "popular":
            saved_tracks_queryset = saved_tracks_queryset.order_by("-views", "-created_at")
        elif saved_sort == "title":
            saved_tracks_queryset = saved_tracks_queryset.order_by("title")
        else:
            saved_sort = "recent"

        saved_tracks = list(saved_tracks_queryset)
        saved_tracks_count = len(saved_tracks)
        queue_duration_seconds = sum(item.track.duration_seconds for item in queue if item.track)
        library_stats = {
            "saved_tracks": request.user.saved_tracks.count(),
            "playlists": request.user.playlists.count(),
            "history_items": request.user.listening_history.count(),
            "queue_items": request.user.queue_items.count(),
            "followed_artists": request.user.followed_artists.count(),
        }
        continue_listening = recent_distinct_tracks(request.user, limit=4)
        for_you_tracks = build_personal_mix(request.user, limit=6)
    return render(
        request,
        "library.html",
        {
            "saved_tracks": saved_tracks,
            "playlists": playlists,
            "history": history,
            "queue": queue,
            "user_profile": user_profile,
            "post_form": post_form,
            "library_stats": library_stats,
            "continue_listening": continue_listening,
            "for_you_tracks": for_you_tracks,
            "saved_query": saved_query,
            "saved_mood": saved_mood,
            "saved_sort": saved_sort,
            "saved_tracks_count": saved_tracks_count,
            "queue_duration_seconds": queue_duration_seconds,
            "queue_duration_label": format_duration_label(queue_duration_seconds),
            "track_moods": Track.MOOD_CHOICES,
            "page_title": "مكتبتي",
            "page_description": "لوحة شخصية تجمع محفوظاتك وطابورك وسجل الاستماع والمقترحات الخاصة بك.",
        },
    )


@require_POST
@login_required
def create_playlist(request):
    name = (request.POST.get("name") or "").strip()
    description = (request.POST.get("description") or "").strip()
    is_public = request.POST.get("is_public") == "on"

    if not name:
        messages.error(request, "اكتب اسمًا لقائمة التشغيل.")
        return redirect("library")

    playlist = Playlist.objects.create(
        name=name,
        description=description,
        is_public=is_public,
        user=request.user,
    )
    messages.success(request, f"تم إنشاء قائمة {playlist.name}.")
    return redirect("playlist_detail", playlist_id=playlist.id)


@require_POST
@login_required
def remove_from_queue(request, item_id):
    QueueItem.objects.filter(id=item_id, user=request.user).delete()
    messages.success(request, "تمت إزالة المقطع من الطابور.")
    return redirect("library")


@require_POST
@login_required
def clear_queue(request):
    QueueItem.objects.filter(user=request.user).delete()
    messages.success(request, "تم مسح قائمة التشغيل التالية.")
    return redirect("library")


@require_POST
@login_required
def create_post(request):
    form = UserPostForm(request.POST, request.FILES)
    if form.is_valid():
        post = form.save(commit=False)
        post.user = request.user
        post.save()
        messages.success(request, "تم نشر منشورك بنجاح.")
    else:
        messages.error(request, "تعذر نشر المنشور. تحقق من النص أو الصورة.")
    return safe_redirect_back(request, "profile_detail_self")


@require_POST
@login_required
def like_post(request, post_id):
    post = get_object_or_404(UserPost, id=post_id, is_published=True)
    if post.likes.filter(id=request.user.id).exists():
        post.likes.remove(request.user)
        messages.success(request, "تمت إزالة الإعجاب من المنشور.")
    else:
        post.likes.add(request.user)
        messages.success(request, "تم تسجيل إعجابك بالمنشور.")
    return safe_redirect_back(request, "community")


@require_POST
@login_required
def add_post_comment(request, post_id):
    post = get_object_or_404(UserPost, id=post_id, is_published=True)
    body = (request.POST.get("body") or "").strip()

    if not body:
        messages.error(request, "اكتب تعليقًا قبل الإرسال.")
        return safe_redirect_back(request, "community")

    if len(body) > 600:
        messages.error(request, "التعليق طويل جدًا. الحد الأقصى 600 حرف.")
        return safe_redirect_back(request, "community")

    PostComment.objects.create(post=post, user=request.user, body=body)
    messages.success(request, "تمت إضافة تعليقك.")
    return safe_redirect_back(request, "community")


def search(request):
    query = (request.GET.get("q") or "").strip()
    mood = request.GET.get("mood") or ""
    category_id = request.GET.get("category") or ""
    sort = request.GET.get("sort") or "relevant"
    duration_bucket = request.GET.get("duration") or ""
    selected_category = None
    results = published_tracks()

    if query:
        results = results.filter(
            Q(title__icontains=query)
            | Q(artist__name__icontains=query)
            | Q(album__title__icontains=query)
            | Q(description__icontains=query)
            | Q(lyrics__icontains=query)
        )
    elif not (mood or category_id):
        results = results.none()

    if mood:
        results = results.filter(mood=mood)
    if category_id:
        results = results.filter(category_id=category_id)
        selected_category = Category.objects.filter(id=category_id).first()
    if duration_bucket:
        results = apply_duration_bucket(results, duration_bucket)

    if sort == "popular":
        results = results.order_by("-views", "-created_at")
    elif sort == "latest":
        results = results.order_by("-created_at")
    elif query:
        results = results.order_by("-views", "-is_featured", "-created_at")
    else:
        sort = "popular"
        results = results.order_by("-is_featured", "-views", "-created_at")

    results_page = paginate_queryset(request, results, per_page=24)
    seo_payload = build_search_page_seo(query, mood, selected_category, duration_bucket)

    return render(
        request,
        "search.html",
        {
            "results": results_page,
            "results_page": results_page,
            "query": query,
            "mood": mood,
            "category_id": category_id,
            "sort": sort,
            "duration_bucket": duration_bucket,
            "moods": Track.MOOD_CHOICES,
            "categories": Category.objects.all(),
            "mood_spotlights": build_mood_spotlights(limit=5, tracks_per_mood=1),
            "search_collections": build_search_collections(query),
            "duration_options": duration_bucket_options(),
            "page_title": f"نتائج البحث عن {query}" if query else "البحث",
            "page_description": "ابحث في المقاطع والفنانين والألبومات والقوائم العامة داخل نغم.",
            "page_noindex": bool(query or mood or category_id or duration_bucket),
            "page_title": seo_payload["title"],
            "page_description": seo_payload["description"],
            "page_noindex": seo_payload["noindex"],
            "page_canonical": seo_payload["canonical"],
        },
    )


def charts(request):
    tracks = published_tracks().order_by("-views", "-created_at")
    tracks_page = paginate_queryset(request, tracks, per_page=20)
    return render(request, "charts.html", {"tracks": tracks_page, "tracks_page": tracks_page})


def discover(request):
    payload = cached_payload("page:discover:public:v1", 180, build_discover_public_payload)
    response = render(
        request,
        "discover.html",
        payload,
    )
    patch_cache_control(response, public=True, max_age=120, stale_while_revalidate=120)
    return response


def community(request):
    posts = paginate_queryset(
        request,
        community_posts_queryset(viewer=request.user).order_by("-created_at"),
        per_page=12,
    )
    public_payload = cached_payload("page:community:public:v1", 180, build_community_public_payload)
    recommended_posts = (
        build_recommended_posts(request.user, limit=6)
        if request.user.is_authenticated
        else public_payload["recommended_posts"]
    )

    response = render(
        request,
        "community.html",
        {
            "posts": posts,
            "posts_page": posts,
            "community_tracks": public_payload["community_tracks"],
            "community_playlists": public_payload["community_playlists"],
            "community_artists": public_payload["community_artists"],
            "trending_categories": public_payload["trending_categories"],
            "community_stats": public_payload["community_stats"],
            "recommended_posts": recommended_posts,
        },
    )
    if not request.user.is_authenticated:
        patch_cache_control(response, public=True, max_age=120, stale_while_revalidate=120)
    return response


def artists(request):
    artists_list = spotlight_artists().order_by("name")
    artists_page = paginate_queryset(request, artists_list, per_page=24)
    return render(
        request,
        "artists.html",
        {
            "artists": artists_page,
            "artists_page": artists_page,
            "page_title": "الفنانون",
            "page_description": "تصفح الفنانين والأصوات البارزة داخل نغم.",
        },
    )


def artist_detail(request, artist_id):
    artist = get_object_or_404(
        Artist.objects.annotate(
            track_count=Count("tracks", distinct=True),
            followers_count=Count("followers", distinct=True),
        ),
        id=artist_id,
    )
    tracks = published_tracks().filter(artist=artist)
    tracks_page = paginate_queryset(request, tracks, per_page=24, page_param="tracks_page")
    albums = artist.albums.annotate(tracks_count=Count("tracks", distinct=True))
    albums_page = paginate_queryset(request, albums, per_page=12, page_param="albums_page")
    related_artists = spotlight_artists().exclude(id=artist.id)[:4]
    artist_categories = (
        Category.objects.filter(tracks__artist=artist)
        .annotate(track_count=Count("tracks", filter=Q(tracks__artist=artist), distinct=True))
        .order_by("-track_count", "name")[:4]
    )
    return render(
        request,
        "artist.html",
        {
            "artist": artist,
            "tracks": tracks_page,
            "tracks_page": tracks_page,
            "albums": albums_page,
            "albums_page": albums_page,
            "related_artists": related_artists,
            "artist_categories": artist_categories,
            "is_following_artist": request.user.is_authenticated
            and artist.followers.filter(id=request.user.id).exists(),
            "page_title": artist.name,
            "page_description": artist.bio or f"استمع إلى مقاطع {artist.name} على نغم.",
            "page_image": artist.image.url if artist.image else "",
        },
    )


@require_POST
@login_required
def follow_artist(request, artist_id):
    artist = get_object_or_404(Artist, id=artist_id)
    if artist.followers.filter(id=request.user.id).exists():
        artist.followers.remove(request.user)
        messages.success(request, f"تم إلغاء متابعة {artist.name}.")
    else:
        artist.followers.add(request.user)
        messages.success(request, f"أنت تتابع {artist.name} الآن.")
    return safe_redirect_back(request, "artists")


def albums(request):
    albums_list = latest_albums()
    albums_page = paginate_queryset(request, albums_list, per_page=24)
    return render(
        request,
        "albums.html",
        {
            "albums": albums_page,
            "albums_page": albums_page,
            "page_title": "الألبومات",
            "page_description": "استكشف الألبومات والإصدارات الحديثة داخل نغم.",
        },
    )


def album_detail(request, album_id):
    album = get_object_or_404(Album.objects.select_related("artist", "category"), id=album_id)
    tracks = published_tracks().filter(album=album)
    tracks_page = paginate_queryset(request, tracks, per_page=24)
    album_tracks_preview = list(tracks[:8])
    related_albums = (
        latest_albums()
        .exclude(id=album.id)
        .filter(Q(artist=album.artist) | Q(category=album.category))[:4]
    )
    return render(
        request,
        "album.html",
        {
            "album": album,
            "tracks": tracks_page,
            "tracks_page": tracks_page,
            "album_tracks_preview": album_tracks_preview,
            "album_track_count": tracks.count(),
            "album_total_duration": sum(track.duration_seconds for track in album_tracks_preview),
            "album_total_duration_label": format_duration_label(
                sum(track.duration_seconds for track in album_tracks_preview)
            ),
            "related_albums": related_albums,
            "page_title": album.title,
            "page_description": album.description or f"ألبوم {album.title} بصوت {album.artist.name}.",
            "page_image": album.cover.url if album.cover else "",
        },
    )


def categories(request):
    categories_list = Category.objects.annotate(track_count=Count("tracks")).order_by("name")
    categories_page = paginate_queryset(request, categories_list, per_page=24)
    return render(
        request,
        "categories.html",
        {"categories": categories_page, "categories_page": categories_page},
    )


def category_detail(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    tracks = published_tracks().filter(category=category)
    tracks_page = paginate_queryset(request, tracks, per_page=24)
    return render(
        request,
        "category.html",
        {
            "category": category,
            "tracks": tracks_page,
            "tracks_page": tracks_page,
            "page_title": category.name,
            "page_description": category.description or f"تصفح مقاطع تصنيف {category.name} على نغم.",
        },
    )


def playlists(request):
    playlists_page = paginate_queryset(request, public_playlists(), per_page=24)
    return render(
        request,
        "playlists.html",
        {
            "playlists": playlists_page,
            "playlists_page": playlists_page,
            "page_title": "قوائم التشغيل",
            "page_description": "استكشف القوائم العامة المنشورة من المجتمع داخل نغم.",
        },
    )


def playlist_detail(request, playlist_id):
    playlist = get_object_or_404(
        Playlist.objects.select_related("user").annotate(tracks_count=Count("tracks", distinct=True)),
        Q(is_public=True) | Q(user=request.user) if request.user.is_authenticated else Q(is_public=True),
        id=playlist_id,
    )
    playlist_tracks_queryset = published_tracks().filter(playlists=playlist)
    tracks_page = paginate_queryset(request, playlist_tracks_queryset, per_page=24)
    playlist_preview_tracks = list(playlist_tracks_queryset[:6])
    return render(
        request,
        "playlist.html",
        {
            "playlist": playlist,
            "tracks": tracks_page,
            "tracks_page": tracks_page,
            "playlist_preview_tracks": playlist_preview_tracks,
            "playlist_total_duration": sum(
                track.duration_seconds for track in playlist_preview_tracks
            ),
            "playlist_total_duration_label": format_duration_label(
                sum(track.duration_seconds for track in playlist_preview_tracks)
            ),
            "related_playlists": build_related_playlists(playlist),
            "page_title": playlist.name,
            "page_description": playlist.description
            or f"استمع إلى قائمة {playlist.name} المنشورة بواسطة {playlist.user.username}.",
            "page_image": playlist.cover.url if playlist.cover else "",
            "page_noindex": not playlist.is_public,
        },
    )


def profile_detail(request, username=None):
    target_user = request.user if username is None and request.user.is_authenticated else None
    if username:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        target_user = get_object_or_404(User, username=username)
    if target_user is None:
        return redirect("login")

    profile = get_profile(target_user)
    posts = community_posts_queryset(viewer=request.user).filter(user=target_user)
    post_form = UserPostForm() if request.user == target_user else None
    return render(
        request,
        "profile_detail.html",
        {
            "profile_user": target_user,
            "profile": profile,
            "posts": posts,
            "post_form": post_form,
            "is_own_profile": request.user.is_authenticated and request.user == target_user,
            "page_title": profile.name,
            "page_description": profile.bio or f"الملف الشخصي للمستخدم {target_user.username} على نغم.",
            "page_image": profile.avatar.url if profile.avatar else "",
        },
    )


@login_required
def profile_edit(request):
    profile = get_profile(request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث ملفك الشخصي.")
            return redirect("profile_detail_self")
    else:
        form = ProfileForm(instance=profile)

    return render(
        request,
        "profile_edit.html",
        {"form": form, "profile": profile, "page_title": "تعديل الملف الشخصي"},
    )
