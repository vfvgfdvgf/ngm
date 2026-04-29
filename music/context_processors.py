import re

from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone

from .models import (
    Announcement,
    Artist,
    FAQ,
    LegalPage,
    PageBanner,
    Playlist,
    SEOPage,
    SiteSettings,
    Track,
    UserProfile,
)


BANNER_IMAGE_WARM = "https://images.unsplash.com/photo-1579546928937-641f7ac9bced?auto=format&fit=crop&fm=jpg&ixid=M3wxMjA3fDB8MHxleHBsb3JlLWZlZWR8MjR8fHxlbnwwfHx8fHw%3D&ixlib=rb-4.1.0&q=60&w=3000"
BANNER_IMAGE_COOL = "https://images.unsplash.com/photo-1557683316-973673baf926?auto=format&fit=crop&fm=jpg&ixid=M3wxMjA3fDB8MHxleHBsb3JlLWZlZWR8MTJ8fHxlbnwwfHx8fHw%3D&ixlib=rb-4.1.0&q=60&w=3000"
BANNER_IMAGE_LIGHT = "https://images.unsplash.com/photo-1523821741446-edb2b68bb7a0?auto=format&fit=crop&fm=jpg&ixid=M3wxMjA3fDB8MHxleHBsb3JlLWZlZWR8MzF8fHxlbnwwfHx8fHw%3D&ixlib=rb-4.1.0&q=60&w=3000"


PAGE_HEADER_DEFAULTS = {
    "home": {"eyebrow": "منصة نغم", "title": "مكتبة صوتية نظيفة بروح كلاسيكية.", "description": "استمع واكتشف واحتفظ بالمقاطع والمنشورات في تجربة عربية أنيقة.", "image_url": BANNER_IMAGE_WARM},
    "discover": {"eyebrow": "اكتشاف", "title": "اختيارات متجددة كل زيارة.", "description": "تجول بين المقاطع والتصنيفات والوجوه الجديدة في تجربة سريعة وواضحة.", "image_url": BANNER_IMAGE_COOL},
    "charts": {"eyebrow": "الترند الهادئ", "title": "الأكثر حضورًا هذا الوقت.", "description": "تابع المقاطع الأعلى استماعًا داخل المنصة.", "image_url": BANNER_IMAGE_COOL},
    "library": {"eyebrow": "مساحتك الخاصة", "title": "كل ما حفظته في مكان واحد.", "description": "المحفوظات والطابور وقوائم التشغيل ومنشوراتك الشخصية.", "image_url": BANNER_IMAGE_WARM},
    "favorites": {"eyebrow": "المفضلة", "title": "مقاطعك الأقرب إليك.", "description": "الوصول السريع إلى كل ما نال إعجابك.", "image_url": BANNER_IMAGE_LIGHT},
    "search": {"eyebrow": "بحث", "title": "اعثر على ما تريد بدقة.", "description": "ابحث بالاسم أو الوصف أو المنشد أو كلمات المقطع.", "image_url": BANNER_IMAGE_LIGHT},
    "artists": {"eyebrow": "فنانون", "title": "تصفح الأصوات والمنشدين.", "description": "تعرف على الفنانين وابدأ رحلتك معهم.", "image_url": BANNER_IMAGE_COOL},
    "artist_detail": {"eyebrow": "فنان", "title": "نبذة ومسيرة ومقاطع الفنان.", "description": "صفحة تجمع الألبومات والمقاطع والهوية البصرية للفنان.", "image_url": BANNER_IMAGE_COOL},
    "albums": {"eyebrow": "ألبومات", "title": "إصدارات متسلسلة بنَفَس كلاسيكي.", "description": "استعرض الألبومات وتفاصيل كل إصدار.", "image_url": BANNER_IMAGE_WARM},
    "album_detail": {"eyebrow": "ألبوم", "title": "تفاصيل الإصدار ومحتواه.", "description": "غلاف الألبوم ووصفه ومقاطع الاستماع داخله.", "image_url": BANNER_IMAGE_WARM},
    "categories": {"eyebrow": "تصنيفات", "title": "رتب مزاجك قبل الاستماع.", "description": "انتقل بين الأنواع والتوجهات بسهولة.", "image_url": BANNER_IMAGE_LIGHT},
    "category_detail": {"eyebrow": "تصنيف", "title": "مقاطع من نفس الطابع.", "description": "مجموعة مركزة تسهّل عليك اختيار ما يناسبك.", "image_url": BANNER_IMAGE_LIGHT},
    "playlists": {"eyebrow": "قوائم التشغيل", "title": "قوائم عامة من المجتمع.", "description": "استعرض القوائم المنشورة من المستخدمين.", "image_url": BANNER_IMAGE_COOL},
    "community": {"eyebrow": "المجتمع", "title": "مساحة نابضة للمشاركات والقوائم والاكتشاف.", "description": "تابع أحدث منشورات المجتمع، القوائم العامة، والأصوات الأكثر حضورًا داخل نغم.", "image_url": BANNER_IMAGE_COOL},
    "playlist_detail": {"eyebrow": "قائمة تشغيل", "title": "استماع مرتب وجاهز.", "description": "كل المقاطع المرتبطة داخل قائمة واحدة.", "image_url": BANNER_IMAGE_COOL},
    "track_detail": {"eyebrow": "الآن يعرض", "title": "معلومات المقطع والتفاعل حوله.", "description": "استمع وعلّق واحفظ وأضف إلى قوائمك.", "image_url": BANNER_IMAGE_WARM},
    "login": {"eyebrow": "عودة سريعة", "title": "ادخل إلى حسابك.", "description": "تابع مكتبتك ومنشوراتك وتفضيلاتك فورًا.", "image_url": BANNER_IMAGE_LIGHT},
    "signup": {"eyebrow": "حساب جديد", "title": "ابدأ حضورك داخل نغم.", "description": "أنشئ حسابًا وخصص ملفك الشخصي وانشر أفكارك.", "image_url": BANNER_IMAGE_LIGHT},
    "profile_detail": {"eyebrow": "الملف الشخصي", "title": "صورتك ونبذتك ومنشوراتك.", "description": "صفحة شخصية قابلة للتخصيص والمشاركة.", "image_url": BANNER_IMAGE_COOL},
    "profile_edit": {"eyebrow": "تخصيص الحساب", "title": "حدّث هويتك داخل المنصة.", "description": "ارفع الصورة الشخصية والبنر وعدّل الوصف والروابط.", "image_url": BANNER_IMAGE_LIGHT},
    "legal_pages": {"eyebrow": "قانوني", "title": "معلومات وسياسات المنصة.", "description": "كل الصفحات القانونية والأسئلة المتكررة في مكان واحد.", "image_url": BANNER_IMAGE_LIGHT},
    "legal_page_detail": {"eyebrow": "صفحة قانونية", "title": "تفاصيل الصفحة القانونية.", "description": "اقرأ النص الكامل للسياسات والشروط.", "image_url": BANNER_IMAGE_LIGHT},
}

PAGE_KEYWORD_DEFAULTS = {
    "home": "نغم, أناشيد, مقاطع صوتية, بودكاست عربي, صوت بلا موسيقى, استماع عربي, مكتبة صوتية",
    "discover": "اكتشف أناشيد, اكتشاف مقاطع, توصيات صوتية, تصنيفات صوتية, منشدون, ألبومات عربية",
    "charts": "الأكثر استماعًا, ترند الأناشيد, مقاطع شائعة, أفضل المقاطع الصوتية, الأكثر حضورًا",
    "library": "مكتبتي, المقاطع المحفوظة, قوائم التشغيل, الطابور, سجل الاستماع",
    "favorites": "المفضلة, المقاطع المفضلة, حفظ المقاطع, إعجابات المستخدم",
    "search": "البحث في نغم, البحث عن أناشيد, كلمات المقاطع, البحث عن منشد, بحث صوتي عربي",
    "artists": "منشدون, فنانون, أصوات عربية, صفحات الفنانين, متابعة المنشدين",
    "artist_detail": "أعمال الفنان, أناشيد الفنان, ألبومات الفنان, مقاطع الفنان",
    "albums": "ألبومات, إصدارات صوتية, ألبومات عربية, قوائم الألبومات",
    "album_detail": "تفاصيل الألبوم, أغاني الألبوم, مقاطع الألبوم, غلاف الألبوم",
    "categories": "تصنيفات, أناشيد هادئة, تركيز, أطفال, صباحي, إيماني",
    "category_detail": "مقاطع حسب التصنيف, اكتشاف حسب المزاج, مقاطع مشابهة",
    "playlists": "قوائم تشغيل, قوائم عامة, تشغيل مستمر, قوائم صوتية عربية",
    "playlist_detail": "تفاصيل قائمة التشغيل, مقاطع القائمة, استماع مرتب",
    "track_detail": "تفاصيل المقطع, استماع مباشر, كلمات المقطع, تعليق على المقطع",
    "community": "مجتمع نغم, منشورات المستخدمين, مشاركة المقاطع, تفاعل المجتمع",
    "login": "تسجيل الدخول, دخول نغم, حساب المستخدم",
    "signup": "إنشاء حساب, تسجيل حساب جديد, الانضمام إلى نغم",
    "profile_detail": "الملف الشخصي, منشورات المستخدم, نشاط الحساب",
    "profile_edit": "تعديل الملف الشخصي, تخصيص الحساب, صورة شخصية, بنر الحساب",
    "legal_pages": "سياسة الخصوصية, الشروط والأحكام, الصفحات القانونية, أسئلة شائعة",
    "legal_page_detail": "الشروط, الخصوصية, سياسات الاستخدام, معلومات قانونية",
}


PAGE_HEADER_DEFAULTS.update(
    {
        "home": {
            "eyebrow": "نغَم",
            "title": "الأغاني بصوت صافي 100% — بدون موسيقى.",
            "description": "استمتع بصوت المغني الحقيقي بجودة عالية، سواء تبيها للمتعة أو للمونتاج وصناعة المحتوى. كل شيء جاهز، سريع، وبضغطة زر.",
            "image_url": BANNER_IMAGE_WARM,
        },
        "discover": {
            "eyebrow": "اكتشف",
            "title": "لف بين الأغاني الأكابيلا بسرعة وبدون لف ودوران.",
            "description": "هنا تلقى مقاطع بدون موسيقى، تصنيفات مرتبة، وأصوات تناسب ذوقك إذا كنت تسمع أو تجهز شغلك للمحتوى.",
            "image_url": BANNER_IMAGE_COOL,
        },
        "community": {
            "eyebrow": "المجتمع",
            "title": "شارك، اكتشف، وخذ الزين من ناس يحبون الصوت الصافي مثلك.",
            "description": "تابع مشاركات المجتمع وقوائمهم واختياراتهم من الأغاني بدون موسيقى داخل مساحة سريعة وواضحة.",
            "image_url": BANNER_IMAGE_COOL,
        },
        "track_detail": {
            "eyebrow": "شغّل الآن",
            "title": "استمع للصوت الحقيقي بدون موسيقى.",
            "description": "كل تفاصيل المقطع قدامك: تشغيل سريع، حفظ، مشاركة، وتعليقات على نفس الصفحة.",
            "image_url": BANNER_IMAGE_WARM,
        },
    }
)

PAGE_KEYWORD_DEFAULTS.update(
    {
        "home": "نغَم, أغاني بدون موسيقى, أكابيلا عربي, Acapella, صوت صافي, صوت المغني الحقيقي, أغاني للمونتاج, صناعة محتوى, أغاني بدون إيقاع, أغاني صافية",
        "discover": "اكتشف أغاني بدون موسيقى, أكابيلا عربي, مقاطع صافية, أغاني للمونتاج, مكتبة أكابيلا, أصوات عربية صافية",
        "community": "مجتمع نغَم, مشاركة أغاني بدون موسيقى, قوائم أكابيلا, محتوى صوتي عربي, مجتمع صناعة محتوى",
        "track_detail": "استماع أكابيلا, أغنية بدون موسيقى, صوت المغني الحقيقي, تحميل أفكار للمونتاج, مقطع صوت صافي",
    }
)

ANALYTICS_ID_PATTERN = re.compile(r"\b(G-[A-Z0-9]+|GTM-[A-Z0-9]+|UA-\d+-\d+)\b")


def extract_analytics_id(raw_value):
    if not raw_value:
        return ""
    match = ANALYTICS_ID_PATTERN.search(raw_value.strip().upper())
    return match.group(1) if match else ""


def resolve_page_keywords(page_key, seo, site_settings):
    raw_keywords = (seo.meta_keywords if seo else "") or ""
    normalized = raw_keywords.strip().lower()
    if normalized and "demo" not in normalized and "test" not in normalized:
        return raw_keywords
    return PAGE_KEYWORD_DEFAULTS.get(page_key, site_settings.default_keywords)


def site_content(request):
    site_settings = cache.get("site_settings_singleton")
    if site_settings is None:
        site_settings = SiteSettings.load()
        cache.set("site_settings_singleton", site_settings, 300)

    page_key = request.resolver_match.url_name if request.resolver_match else ""
    seo = cache.get(f"seo_page::{page_key}")
    if seo is None:
        seo = SEOPage.objects.filter(page_key=page_key).first()
        cache.set(f"seo_page::{page_key}", seo, 300)

    page_banners = cache.get(f"page_banners::{page_key}")
    if page_banners is None:
        page_banners = list(
            PageBanner.objects.filter(page_key=page_key, is_active=True).order_by("sort_order", "id")
        )
        cache.set(f"page_banners::{page_key}", page_banners, 300)

    banner_defaults = PAGE_HEADER_DEFAULTS.get(page_key, {})
    now = timezone.now()
    announcement = cache.get("active_announcement")
    if announcement is None:
        announcement = (
            Announcement.objects.filter(is_active=True)
            .filter(Q(starts_at__isnull=True) | Q(starts_at__lte=now))
            .filter(Q(ends_at__isnull=True) | Q(ends_at__gte=now))
            .first()
        )
        cache.set("active_announcement", announcement, 60)

    current_profile = None
    request_user = getattr(request, "user", None)
    if request_user and request_user.is_authenticated:
        current_profile = UserProfile.objects.filter(user=request_user).first()

    request_base_url = request.build_absolute_uri("/").rstrip("/")
    site_base_url = (site_settings.canonical_domain or request_base_url).rstrip("/")
    page_banner_items = []
    page_banner_slots = {}
    for banner in page_banners:
        image_url = ""
        if banner.image:
            image_url = banner.image.url
        elif banner.image_url:
            image_url = banner.image_url
        item = {
            "eyebrow": banner.eyebrow or banner_defaults.get("eyebrow", ""),
            "title": banner.title or banner_defaults.get("title", ""),
            "description": banner.description or banner_defaults.get("description", ""),
            "image_url": image_url or banner_defaults.get("image_url", ""),
            "primary_label": banner.primary_label,
            "primary_url": banner.primary_url,
            "secondary_label": banner.secondary_label,
            "secondary_url": banner.secondary_url,
            "placement": banner.placement,
            "size": banner.size,
        }
        page_banner_items.append(item)
        page_banner_slots.setdefault(banner.placement, []).append(item)

    if not page_banner_items and banner_defaults:
        default_item = {
            "eyebrow": banner_defaults.get("eyebrow", ""),
            "title": banner_defaults.get("title", ""),
            "description": banner_defaults.get("description", ""),
            "image_url": banner_defaults.get("image_url", ""),
            "primary_label": "",
            "primary_url": "",
            "secondary_label": "",
            "secondary_url": "",
            "placement": "top",
            "size": "hero",
        }
        page_banner_items.append(default_item)
        page_banner_slots["top"] = [default_item]

    page_banner = page_banners[0] if page_banners else None
    page_banner_image_url = page_banner_items[0]["image_url"] if page_banner_items else ""

    footer_legal_pages = cache.get("footer_legal_pages")
    if footer_legal_pages is None:
        footer_legal_pages = list(LegalPage.objects.filter(is_published=True, show_in_footer=True)[:8])
        cache.set("footer_legal_pages", footer_legal_pages, 300)

    footer_stats = cache.get("footer_stats")
    if footer_stats is None:
        footer_stats = {
            "tracks": Track.objects.filter(is_published=True).count(),
            "artists": Artist.objects.count(),
            "playlists": Playlist.objects.filter(is_public=True).count(),
            "faqs": FAQ.objects.filter(is_active=True).count(),
        }
        cache.set("footer_stats", footer_stats, 300)

    footer_featured_pages = cache.get("footer_featured_pages")
    if footer_featured_pages is None:
        footer_featured_pages = list(
            LegalPage.objects.filter(is_published=True).order_by("-updated_at").values(
                "title", "slug", "updated_at"
            )[:3]
        )
        cache.set("footer_featured_pages", footer_featured_pages, 300)

    return {
        "site_settings": site_settings,
        "site_base_url": site_base_url,
        "global_seo": seo,
        "page_keywords": resolve_page_keywords(page_key, seo, site_settings),
        "page_banner": page_banner,
        "page_banners": page_banners,
        "page_banner_items": page_banner_items,
        "page_banner_slots": page_banner_slots,
        "page_banner_defaults": banner_defaults,
        "page_banner_image_url": page_banner_image_url,
        "footer_legal_pages": footer_legal_pages,
        "footer_featured_pages": footer_featured_pages,
        "footer_stats": footer_stats,
        "current_year": timezone.now().year,
        "active_announcement": announcement,
        "current_profile": current_profile,
        "analytics_id": extract_analytics_id(site_settings.analytics_code),
    }
