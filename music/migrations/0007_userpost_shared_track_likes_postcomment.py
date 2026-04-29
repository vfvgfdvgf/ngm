from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("music", "0006_pagebanner_image_url_and_seed_defaults"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="userpost",
            name="likes",
            field=models.ManyToManyField(
                blank=True,
                related_name="liked_posts",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="userpost",
            name="shared_track",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="shared_posts",
                to="music.track",
            ),
        ),
        migrations.CreateModel(
            name="PostComment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("body", models.TextField(max_length=600)),
                ("is_visible", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "post",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="comments",
                        to="music.userpost",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="post_comments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="postcomment",
            index=models.Index(fields=["-created_at"], name="music_postc_created_62066f_idx"),
        ),
        migrations.AddIndex(
            model_name="postcomment",
            index=models.Index(fields=["is_visible"], name="music_postc_is_visi_63cb80_idx"),
        ),
    ]
