from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("music", "0009_securityevent_blockedip"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="VisitEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("path", models.CharField(max_length=500)),
                ("method", models.CharField(default="GET", max_length=8)),
                ("status_code", models.PositiveSmallIntegerField(default=200)),
                ("response_ms", models.PositiveIntegerField(default=0)),
                ("ip_address", models.GenericIPAddressField()),
                ("country_code", models.CharField(blank=True, max_length=8)),
                ("user_agent", models.TextField(blank=True)),
                ("referer", models.CharField(blank=True, max_length=500)),
                ("is_staff_request", models.BooleanField(default=False)),
                ("visited_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="visit_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-visited_at"]},
        ),
        migrations.AddIndex(
            model_name="visitevent",
            index=models.Index(fields=["-visited_at"], name="music_visit_visited_23f4f7_idx"),
        ),
        migrations.AddIndex(
            model_name="visitevent",
            index=models.Index(fields=["ip_address", "-visited_at"], name="music_visit_ip_addr_9f6b90_idx"),
        ),
        migrations.AddIndex(
            model_name="visitevent",
            index=models.Index(fields=["country_code", "-visited_at"], name="music_visit_country_87d2de_idx"),
        ),
        migrations.AddIndex(
            model_name="visitevent",
            index=models.Index(fields=["path", "-visited_at"], name="music_visit_path_1da02c_idx"),
        ),
    ]
