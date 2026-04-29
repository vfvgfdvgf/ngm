from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("music", "0008_rename_music_postc_created_62066f_idx_music_postc_created_8c5513_idx_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="SecurityEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ip_address", models.GenericIPAddressField()),
                ("path", models.CharField(max_length=500)),
                ("user_agent", models.TextField(blank=True)),
                ("reason", models.CharField(max_length=200)),
                (
                    "severity",
                    models.CharField(
                        choices=[("low", "منخفض"), ("medium", "متوسط"), ("high", "مرتفع")],
                        default="medium",
                        max_length=12,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="BlockedIP",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ip_address", models.GenericIPAddressField(unique=True)),
                ("reason", models.CharField(max_length=200)),
                ("expires_at", models.DateTimeField()),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.AddIndex(
            model_name="securityevent",
            index=models.Index(fields=["ip_address", "-created_at"], name="music_secur_ip_addr_4bb9ee_idx"),
        ),
        migrations.AddIndex(
            model_name="securityevent",
            index=models.Index(fields=["severity", "-created_at"], name="music_secur_severi_1fe4d7_idx"),
        ),
        migrations.AddIndex(
            model_name="blockedip",
            index=models.Index(fields=["ip_address", "is_active"], name="music_block_ip_addr_62014e_idx"),
        ),
        migrations.AddIndex(
            model_name="blockedip",
            index=models.Index(fields=["expires_at"], name="music_block_expires_77d4b4_idx"),
        ),
    ]
