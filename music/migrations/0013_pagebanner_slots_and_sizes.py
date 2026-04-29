from django.db import migrations, models


def seed_distributed_banners(apps, schema_editor):
    PageBanner = apps.get_model("music", "PageBanner")

    samples = [
        {
            "page_key": "home",
            "placement": "after_hero",
            "size": "wide",
            "sort_order": 0,
            "title": "مقاطع صافية تجهزها للمحتوى في ثوانٍ",
            "eyebrow": "للمونتاج",
            "description": "إذا تشتغل على ريلز أو يوتيوب أو إعلانات، هنا تلقى صوت نظيف وجاهز بدون لف ودوران.",
            "primary_label": "روح للاكتشاف",
            "primary_url": "/discover/",
            "secondary_label": "افتح البحث",
            "secondary_url": "/search/",
            "is_active": True,
        },
        {
            "page_key": "home",
            "placement": "after_section_2",
            "size": "split",
            "sort_order": 0,
            "title": "قوائم على حسب المزاج",
            "eyebrow": "جاهزة لك",
            "description": "اسمع على حسب صباحك أو تركيزك أو وقت الشغل.",
            "primary_label": "شوف القوائم",
            "primary_url": "/playlists/",
            "secondary_label": "",
            "secondary_url": "",
            "is_active": True,
        },
        {
            "page_key": "home",
            "placement": "after_section_2",
            "size": "split",
            "sort_order": 1,
            "title": "شارك ذوقك مع المجتمع",
            "eyebrow": "مجتمع نغم",
            "description": "خذ أفكار جديدة من الناس اللي يحبون الصوت الصافي مثلك.",
            "primary_label": "ادخل المجتمع",
            "primary_url": "/community/",
            "secondary_label": "",
            "secondary_url": "",
            "is_active": True,
        },
        {
            "page_key": "discover",
            "placement": "after_section_1",
            "size": "wide",
            "sort_order": 0,
            "title": "رتب اكتشافك على كيفك",
            "eyebrow": "فلترة أسرع",
            "description": "تنقل بين التصنيفات والفنانين والمقاطع بشكل أخف وأوضح.",
            "primary_label": "افتح البحث",
            "primary_url": "/search/",
            "secondary_label": "الأكثر استماعًا",
            "secondary_url": "/charts/",
            "is_active": True,
        },
        {
            "page_key": "discover",
            "placement": "after_section_3",
            "size": "compact",
            "sort_order": 0,
            "title": "فنانين يستاهلون",
            "eyebrow": "اقتراح",
            "description": "خذ لفة على الأصوات الجديدة.",
            "primary_label": "كل الفنانين",
            "primary_url": "/artists/",
            "secondary_label": "",
            "secondary_url": "",
            "is_active": True,
        },
        {
            "page_key": "discover",
            "placement": "after_section_3",
            "size": "compact",
            "sort_order": 1,
            "title": "قوائم مرتبة",
            "eyebrow": "استماع سريع",
            "description": "ادخل على قوائم جاهزة واختصر وقتك.",
            "primary_label": "القوائم",
            "primary_url": "/playlists/",
            "secondary_label": "",
            "secondary_url": "",
            "is_active": True,
        },
        {
            "page_key": "community",
            "placement": "after_hero",
            "size": "wide",
            "sort_order": 0,
            "title": "المجتمع هنا يعطيك أفكار أسرع",
            "eyebrow": "نبض نغم",
            "description": "منشورات، قوائم، وتفاعل حول الأغاني بدون موسيقى في مكان واحد.",
            "primary_label": "شوف المشاركات",
            "primary_url": "/community/",
            "secondary_label": "شوف القوائم",
            "secondary_url": "/playlists/",
            "is_active": True,
        },
        {
            "page_key": "community",
            "placement": "after_section_2",
            "size": "split",
            "sort_order": 0,
            "title": "سو حسابك وابدأ شارك",
            "eyebrow": "حساب جديد",
            "description": "ابنِ مكتبتك وشارك المقاطع اللي تعجبك.",
            "primary_label": "إنشاء حساب",
            "primary_url": "/accounts/signup/",
            "secondary_label": "",
            "secondary_url": "",
            "is_active": True,
        },
        {
            "page_key": "community",
            "placement": "after_section_2",
            "size": "split",
            "sort_order": 1,
            "title": "اكتشف المقاطع الشائعة",
            "eyebrow": "شائع الآن",
            "description": "أصوات عليها تفاعل ومشاركة من المجتمع.",
            "primary_label": "الأكثر استماعًا",
            "primary_url": "/charts/",
            "secondary_label": "",
            "secondary_url": "",
            "is_active": True,
        },
    ]

    for sample in samples:
        PageBanner.objects.get_or_create(
            page_key=sample["page_key"],
            placement=sample["placement"],
            sort_order=sample["sort_order"],
            title=sample["title"],
            defaults=sample,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("music", "0012_pagebanner_multiple_per_page"),
    ]

    operations = [
        migrations.AddField(
            model_name="pagebanner",
            name="placement",
            field=models.CharField(
                choices=[
                    ("top", "Top"),
                    ("after_hero", "After hero"),
                    ("after_section_1", "After section 1"),
                    ("after_section_2", "After section 2"),
                    ("after_section_3", "After section 3"),
                    ("bottom", "Bottom"),
                ],
                default="top",
                max_length=40,
            ),
        ),
        migrations.AddField(
            model_name="pagebanner",
            name="size",
            field=models.CharField(
                choices=[
                    ("hero", "Hero"),
                    ("wide", "Wide"),
                    ("split", "Split"),
                    ("compact", "Compact"),
                ],
                default="hero",
                max_length=20,
            ),
        ),
        migrations.RunPython(seed_distributed_banners, migrations.RunPython.noop),
    ]
