from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("music", "0010_visitevent"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="favicon",
            field=models.ImageField(blank=True, null=True, upload_to="branding/"),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="logo",
            field=models.ImageField(blank=True, null=True, upload_to="branding/"),
        ),
    ]
