from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Album, Artist, Category, LegalPage, SiteSettings, Track


User = get_user_model()


class SiteExperienceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.objects.update_or_create(
            pk=1,
            defaults={
                "site_name": "Nagham",
                "canonical_domain": "https://nagham.example.com",
                "header_cta_label": "Join",
                "header_cta_url": "/signup/",
            },
        )
        cls.category = Category.objects.create(name="Nasheeds", description="Test category")
        cls.artist = Artist.objects.create(name="Test Artist", bio="Test bio")
        cls.album = Album.objects.create(
            title="Test Album",
            artist=cls.artist,
            category=cls.category,
            description="Album description",
        )
        cls.track = Track.objects.create(
            title="Test Track",
            artist=cls.artist,
            album=cls.album,
            category=cls.category,
            audio_file="tracks/test.mp3",
            description="Track description",
            duration_seconds=125,
            is_published=True,
        )
        cls.legal_page = LegalPage.objects.create(
            title="Privacy Policy",
            slug="privacy",
            summary="Summary",
            content="Legal content",
            is_published=True,
        )
        cls.user = User.objects.create_user(username="tester", password="pass12345")

    def test_home_contains_canonical_and_twitter_meta(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            '<link rel="canonical" href="https://nagham.example.com/">',
            html=True,
        )
        self.assertContains(
            response,
            '<meta property="og:url" content="https://nagham.example.com/">',
            html=True,
        )
        self.assertContains(response, 'name="twitter:title"', html=False)
        self.assertContains(response, 'href="#main-content"')
        self.assertContains(response, 'rel="manifest"', html=False)
        self.assertContains(response, '"@type": "WebPage"', html=False)
        self.assertContains(response, 'rel="dns-prefetch"', html=False)
        self.assertContains(response, 'rel="preload"', html=False)
        self.assertIn("max-age=120", response["Cache-Control"])

    def test_robots_uses_canonical_domain(self):
        response = self.client.get(reverse("robots_txt"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sitemap: https://nagham.example.com/sitemap.xml")
        self.assertContains(response, "Disallow: /control/")
        self.assertIn("max-age=3600", response["Cache-Control"])

    def test_manifest_route_uses_site_settings(self):
        response = self.client.get(reverse("manifest_webmanifest"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/manifest+json")
        self.assertContains(response, '"name": "Nagham"', html=False)
        self.assertContains(response, '"short_name": "Nagham"', html=False)
        self.assertContains(response, '"start_url": "/"', html=False)
        self.assertContains(response, '"display": "standalone"', html=False)
        self.assertIn("max-age=3600", response["Cache-Control"])

    def test_sitemap_uses_canonical_domain_and_track_url(self):
        response = self.client.get(reverse("sitemap_xml"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "https://nagham.example.com/track/")
        self.assertContains(response, "https://nagham.example.com/legal/privacy/")
        self.assertContains(response, "https://nagham.example.com/community/")
        self.assertIn("max-age=1800", response["Cache-Control"])

    def test_track_detail_sets_meta_without_incrementing_views(self):
        response = self.client.get(reverse("track_detail", args=[self.track.id]))
        self.assertEqual(response.status_code, 200)
        self.track.refresh_from_db()
        self.assertEqual(self.track.views, 0)
        self.assertContains(response, self.track.title)
        self.assertContains(response, self.artist.name)

    def test_register_track_play_increments_views_once_per_window(self):
        self.assertEqual(self.track.views, 0)
        play_url = reverse("register_track_play", args=[self.track.id])

        first = self.client.post(play_url)
        self.assertEqual(first.status_code, 200)
        self.track.refresh_from_db()
        self.assertEqual(self.track.views, 1)

        second = self.client.post(play_url)
        self.assertEqual(second.status_code, 200)
        self.track.refresh_from_db()
        self.assertEqual(self.track.views, 1)

    def test_signup_page_loads(self):
        response = self.client.get(reverse("signup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "signup")
        self.assertContains(response, "images.unsplash.com")

    def test_community_page_loads(self):
        response = self.client.get(reverse("community"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "community/")
        self.assertContains(response, "images.unsplash.com")

    def test_google_verification_meta_and_custom_head_code_render(self):
        settings_obj = SiteSettings.load()
        settings_obj.google_site_verification = "google-token-123"
        settings_obj.custom_head_code = '<meta name="custom-check" content="ok">'
        settings_obj.save()

        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            '<meta name="google-site-verification" content="google-token-123">',
            html=True,
        )
        self.assertContains(response, '<meta name="custom-check" content="ok">', html=False)

    def test_google_verification_file_route(self):
        settings_obj = SiteSettings.load()
        settings_obj.verification_file_name = "googleabc123.html"
        settings_obj.verification_file_content = "google-site-verification: googleabc123.html"
        settings_obj.save()

        response = self.client.get("/googleabc123.html")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "google-site-verification: googleabc123.html")

    def test_database_media_storage_serves_uploaded_file(self):
        settings_obj = SiteSettings.load()
        settings_obj.logo.save("branding/logo.png", ContentFile(b"fake-image-bytes", name="logo.png"), save=True)

        response = self.client.get(settings_obj.logo.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"fake-image-bytes")
