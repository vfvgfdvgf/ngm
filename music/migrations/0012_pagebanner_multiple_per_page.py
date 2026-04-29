from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("music", "0011_sitesettings_branding"),
    ]

    operations = [
        migrations.AddField(
            model_name="pagebanner",
            name="sort_order",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="pagebanner",
            name="page_key",
            field=models.CharField(
                choices=[
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
                ],
                max_length=80,
            ),
        ),
    ]
