import base64
import io
import math
import random
import urllib.parse
import urllib.request
import wave
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from music.models import (
    PAGE_CHOICES,
    Album,
    Announcement,
    Artist,
    Category,
    FAQ,
    LegalPage,
    ListeningHistory,
    PageBanner,
    Playlist,
    QueueItem,
    SEOPage,
    SiteSettings,
    Track,
    TrackComment,
    UserPost,
    UserProfile,
)


PNG_PIXEL = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WnRkS4AAAAASUVORK5CYII="
)

PICSUM_BASE_URL = "https://picsum.photos/seed/{seed}/{width}/{height}.jpg"


class Command(BaseCommand):
    help = "Seed rich demo data for the Nagham site."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete old demo data first, then recreate it.",
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            if options["reset"]:
                self._reset_demo_data()

            self.password = "DemoPass123!"
            self.user_model = get_user_model()

            users = self._create_users()
            self._create_site_content()
            categories = self._create_categories()
            artists = self._create_artists(users)
            albums = self._create_albums(artists, categories)
            tracks = self._create_tracks(artists, categories, albums)
            playlists = self._create_playlists(users, tracks)
            self._create_posts(users)
            self._create_social_activity(users, artists, tracks, playlists)

        self.stdout.write(self.style.SUCCESS("Demo data created successfully."))
        self.stdout.write("Users:")
        for username in [
            "demo_admin",
            "demo_ahmad",
            "demo_sara",
            "demo_noura",
            "demo_guest",
        ]:
            self.stdout.write(f"  - {username} / {self.password}")

    def _reset_demo_data(self):
        demo_usernames = [
            "demo_admin",
            "demo_ahmad",
            "demo_sara",
            "demo_noura",
            "demo_guest",
        ]
        self.user_model = get_user_model()

        QueueItem.objects.filter(user__username__in=demo_usernames).delete()
        ListeningHistory.objects.filter(user__username__in=demo_usernames).delete()
        TrackComment.objects.filter(user__username__in=demo_usernames).delete()
        UserPost.objects.filter(user__username__in=demo_usernames).delete()
        Playlist.objects.filter(user__username__in=demo_usernames).delete()
        UserProfile.objects.filter(user__username__in=demo_usernames).delete()
        self.user_model.objects.filter(username__in=demo_usernames).delete()

        Track.objects.filter(title__startswith="Demo ").delete()
        Album.objects.filter(title__startswith="Demo ").delete()
        Artist.objects.filter(name__startswith="Demo ").delete()
        Category.objects.filter(name__startswith="Demo ").delete()
        LegalPage.objects.filter(slug__startswith="demo-").delete()
        Announcement.objects.filter(title__startswith="Demo ").delete()
        FAQ.objects.filter(question__startswith="Demo ").delete()
        SEOPage.objects.filter(browser_title__startswith="Demo ").delete()
        PageBanner.objects.filter(title__startswith="Demo ").delete()

    def _content_file(self, filename, content):
        return ContentFile(content, name=filename)

    def _internet_image_bytes(self, seed, width=1200, height=1200):
        seed = urllib.parse.quote_plus(str(seed))
        url = PICSUM_BASE_URL.format(seed=seed, width=width, height=height)
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                return response.read()
        except Exception:
            return PNG_PIXEL

    def _image_file(self, prefix, slug, width=1200, height=1200):
        image_bytes = self._internet_image_bytes(f"{prefix}-{slug}", width=width, height=height)
        return self._content_file(f"{prefix}-{slug}.jpg", image_bytes)

    def _audio_file(self, slug, seconds=3, frequency=440):
        buffer = io.BytesIO()
        sample_rate = 22050
        amplitude = 12000
        frame_count = seconds * sample_rate

        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            frames = bytearray()
            for i in range(frame_count):
                angle = 2 * math.pi * frequency * (i / sample_rate)
                sample = int(amplitude * math.sin(angle))
                frames.extend(sample.to_bytes(2, byteorder="little", signed=True))
            wav_file.writeframes(bytes(frames))

        return self._content_file(f"demo-{slug}.wav", buffer.getvalue())

    def _create_users(self):
        user_specs = [
            ("demo_admin", "مدير تجريبي", True, True, "riyadh"),
            ("demo_ahmad", "أحمد", False, False, "jeddah"),
            ("demo_sara", "سارة", False, False, "dammam"),
            ("demo_noura", "نورة", False, False, "makkah"),
            ("demo_guest", "زائر تجريبي", False, False, "madinah"),
        ]

        users = {}
        for index, (username, display_name, is_staff, is_superuser, city) in enumerate(user_specs, start=1):
            user, created = self.user_model.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.com",
                    "is_staff": is_staff,
                    "is_superuser": is_superuser,
                },
            )
            if created or not user.check_password(self.password):
                user.set_password(self.password)
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.save()

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.display_name = display_name
            profile.bio = f"{display_name} حساب تجريبي لاختبار ميزات المنصة والتفاعل والمكتبة الشخصية."
            profile.location = city
            profile.website = "https://example.com"
            if not profile.avatar:
                profile.avatar.save(
                    f"{username}-avatar.jpg",
                    self._image_file("avatar", username, width=512, height=512),
                    save=False,
                )
            if not profile.banner_image:
                profile.banner_image.save(
                    f"{username}-banner.jpg",
                    self._image_file("banner", username, width=1600, height=600),
                    save=False,
                )
            profile.save()
            users[username] = user

        return users

    def _create_site_content(self):
        settings_obj = SiteSettings.load()
        settings_obj.site_name = "نغم"
        settings_obj.tagline = "منصة صوت بلا موسيقى"
        settings_obj.default_title = "نغم - منصة تجريبية جاهزة للاختبار"
        settings_obj.default_description = "بيانات تجريبية شاملة لتجربة صفحات نغم والمشغل والمجتمع والبحث."
        settings_obj.default_keywords = "نغم,تجربة,اختبار,أناشيد,بودكاست"
        settings_obj.header_cta_label = "سجل الآن"
        settings_obj.header_cta_url = "/signup/"
        settings_obj.maintenance_message = ""
        settings_obj.save()

        legal_pages = [
            (
                "سياسة الخصوصية",
                "demo-privacy",
                "كيف نتعامل مع البيانات داخل النسخة التجريبية.",
            ),
            (
                "شروط الاستخدام",
                "demo-terms",
                "قواعد استخدام المنصة والحسابات والمحتوى.",
            ),
        ]
        for title, slug, summary in legal_pages:
            LegalPage.objects.update_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "summary": summary,
                    "content": f"{title}\n\nهذه صفحة قانونية تجريبية لتعبئة الموقع أثناء الاختبار.",
                    "meta_title": f"Demo {title}",
                    "meta_description": summary,
                    "is_published": True,
                    "show_in_footer": True,
                },
            )

        for index, question in enumerate(
            [
                "Demo كيف أستخدم البحث؟",
                "Demo كيف أحفظ المقاطع؟",
                "Demo كيف أنشئ قائمة تشغيل؟",
            ],
            start=1,
        ):
            FAQ.objects.update_or_create(
                question=question,
                defaults={
                    "answer": "هذه إجابة تجريبية لتوضيح شكل قسم الأسئلة المتكررة أثناء فحص الواجهة.",
                    "is_active": True,
                    "sort_order": index,
                },
            )

        Announcement.objects.update_or_create(
            title="Demo نسخة جاهزة للتجربة",
            defaults={
                "message": "تمت تعبئة الموقع ببيانات تجريبية حتى تختبر جميع الصفحات والميزات.",
                "link_label": "اذهب إلى الاكتشاف",
                "link_url": "/discover/",
                "is_active": True,
                "starts_at": timezone.now() - timedelta(days=1),
                "ends_at": timezone.now() + timedelta(days=30),
            },
        )

        for page_key, page_label in PAGE_CHOICES:
            SEOPage.objects.update_or_create(
                page_key=page_key,
                defaults={
                    "browser_title": f"Demo {page_label}",
                    "meta_description": f"وصف تجريبي لصفحة {page_label} داخل منصة نغم.",
                    "meta_keywords": "demo,nagham,test",
                    "og_title": f"Demo {page_label}",
                    "og_description": f"محتوى تجريبي لصفحة {page_label}.",
                    "noindex": False,
                },
            )
            PageBanner.objects.update_or_create(
                page_key=page_key,
                defaults={
                    "eyebrow": "تجربة جاهزة",
                    "title": f"Demo {page_label}",
                    "description": f"بنر تجريبي لصفحة {page_label} حتى يظهر التصميم كاملًا أثناء الاختبار.",
                    "primary_label": "اكتشف الآن",
                    "primary_url": "/discover/",
                    "secondary_label": "المجتمع",
                    "secondary_url": "/community/",
                    "is_active": True,
                },
            )

    def _create_categories(self):
        categories = []
        for name, description in [
            ("Demo إيماني", "محتوى تعبدي وتأملي هادئ."),
            ("Demo صباحي", "مقاطع خفيفة لبداية اليوم."),
            ("Demo تركيز", "محتوى مناسب للدراسة والعمل."),
            ("Demo أطفال", "محتوى مناسب للعائلة والأطفال."),
            ("Demo قصص", "قصص قصيرة ومحتوى صوتي سردي."),
        ]:
            category, _ = Category.objects.get_or_create(
                name=name,
                defaults={"description": description},
            )
            category.description = description
            if not category.cover:
                category.cover.save(
                    f"{category.name}.jpg",
                    self._image_file("category", category.name.replace(" ", "-"), width=900, height=900),
                    save=False,
                )
            category.save()
            categories.append(category)
        return categories

    def _create_artists(self, users):
        artists = []
        artist_specs = [
            ("Demo عبد الله", True),
            ("Demo هدى", True),
            ("Demo خالد", False),
            ("Demo رنيم", False),
            ("Demo بيان", False),
        ]
        follower_pool = list(users.values())
        for name, verified in artist_specs:
            artist, _ = Artist.objects.get_or_create(
                name=name,
                defaults={"bio": f"{name} فنان تجريبي لاختبار صفحات الفنانين.", "verified": verified},
            )
            artist.bio = f"{name} فنان تجريبي لاختبار صفحات الفنانين والألبومات والمقاطع."
            artist.verified = verified
            if not artist.image:
                artist.image.save(
                    f"{name}.jpg",
                    self._image_file("artist", name.replace(" ", "-"), width=900, height=900),
                    save=False,
                )
            artist.save()
            artist.followers.set(random.sample(follower_pool, k=min(3, len(follower_pool))))
            artists.append(artist)
        return artists

    def _create_albums(self, artists, categories):
        albums = []
        for index in range(1, 7):
            artist = artists[(index - 1) % len(artists)]
            category = categories[(index - 1) % len(categories)]
            album, _ = Album.objects.get_or_create(
                title=f"Demo Album {index}",
                defaults={
                    "artist": artist,
                    "category": category,
                    "description": f"ألبوم تجريبي رقم {index} لتغطية صفحات الألبومات.",
                    "release_date": date.today() - timedelta(days=index * 20),
                },
            )
            album.artist = artist
            album.category = category
            album.description = f"ألبوم تجريبي رقم {index} لتغطية صفحات الألبومات والفهارس."
            album.release_date = date.today() - timedelta(days=index * 20)
            if not album.cover:
                album.cover.save(
                    f"album-{index}.jpg",
                    self._image_file("album", str(index), width=1000, height=1000),
                    save=False,
                )
            album.save()
            albums.append(album)
        return albums

    def _create_tracks(self, artists, categories, albums):
        mood_cycle = [choice[0] for choice in Track.MOOD_CHOICES]
        tracks = []
        for index in range(1, 19):
            artist = artists[(index - 1) % len(artists)]
            category = categories[(index - 1) % len(categories)]
            album = albums[(index - 1) % len(albums)]
            mood = mood_cycle[(index - 1) % len(mood_cycle)]
            track, _ = Track.objects.get_or_create(
                title=f"Demo Track {index}",
                defaults={
                    "artist": artist,
                    "album": album,
                    "category": category,
                    "description": f"مقطع تجريبي رقم {index} لتغطية المشغل والبحث والبطاقات.",
                    "lyrics": f"كلمات تجريبية للمقطع رقم {index}.",
                    "duration_seconds": 90 + index * 7,
                    "mood": mood,
                    "views": index * 17,
                    "is_featured": index <= 6,
                    "is_published": True,
                    "allow_download": index % 2 == 0,
                },
            )
            track.artist = artist
            track.album = album
            track.category = category
            track.description = f"مقطع تجريبي رقم {index} لتغطية المشغل والبحث والبطاقات."
            track.lyrics = f"هذا نص تجريبي للمقطع {index} حتى يظهر قسم الكلمات والتفاصيل."
            track.duration_seconds = 90 + index * 7
            track.mood = mood
            track.views = index * 17
            track.is_featured = index <= 6
            track.is_published = True
            track.allow_download = index % 2 == 0
            if not track.audio_file:
                track.audio_file.save(
                    f"track-{index}.wav",
                    self._audio_file(f"track-{index}", seconds=3, frequency=330 + index * 10),
                    save=False,
                )
            if not track.cover:
                track.cover.save(
                    f"track-{index}.jpg",
                    self._image_file("track", str(index), width=1000, height=1000),
                    save=False,
                )
            track.save()
            tracks.append(track)
        return tracks

    def _create_playlists(self, users, tracks):
        playlist_specs = [
            ("Demo Morning Flow", "demo_ahmad", True, tracks[:6]),
            ("Demo Focus Picks", "demo_sara", True, tracks[4:10]),
            ("Demo Family Time", "demo_noura", True, tracks[8:14]),
            ("Demo Private Queue", "demo_guest", False, tracks[12:18]),
        ]
        playlists = []
        for name, username, is_public, track_subset in playlist_specs:
            playlist, _ = Playlist.objects.get_or_create(
                name=name,
                user=users[username],
                defaults={
                    "description": f"{name} قائمة تشغيل تجريبية لتغطية القوائم العامة والخاصة.",
                    "is_public": is_public,
                },
            )
            playlist.description = f"{name} قائمة تشغيل تجريبية لتغطية القوائم العامة والخاصة."
            playlist.is_public = is_public
            if not playlist.cover:
                playlist.cover.save(
                    f"{name}.jpg",
                    self._image_file("playlist", name.replace(" ", "-"), width=1000, height=1000),
                    save=False,
                )
            playlist.save()
            playlist.tracks.set(track_subset)
            playlists.append(playlist)
        return playlists

    def _create_posts(self, users):
        posts = [
            ("demo_ahmad", "هذا منشور تجريبي لاختبار صفحة المجتمع وتخطيط البطاقات."),
            ("demo_sara", "أجرب اليوم قائمة جديدة للمقاطع الهادئة داخل نغم."),
            ("demo_noura", "واجهة المجتمع أصبحت أوضح مع بيانات حقيقية للتجربة."),
        ]
        for index, (username, body) in enumerate(posts, start=1):
            post, _ = UserPost.objects.get_or_create(
                user=users[username],
                body=body,
                defaults={"is_published": True},
            )
            post.is_published = True
            if index % 2 == 1 and not post.image:
                post.image.save(
                    f"post-{index}.jpg",
                    self._image_file("post", str(index), width=1400, height=900),
                    save=False,
                )
            post.save()

    def _create_social_activity(self, users, artists, tracks, playlists):
        user_list = list(users.values())

        for idx, track in enumerate(tracks):
            liked_by = user_list[: (idx % len(user_list)) + 1]
            saved_by = user_list[idx % len(user_list) :] or user_list[:1]
            track.likes.set(liked_by)
            track.saved_by.set(saved_by[:3])

            for comment_index, user in enumerate(user_list[:3], start=1):
                TrackComment.objects.get_or_create(
                    track=track,
                    user=user,
                    body=f"تعليق تجريبي {comment_index} على {track.title}.",
                    defaults={"is_visible": True},
                )

        for user in user_list:
            for track in random.sample(tracks, k=min(5, len(tracks))):
                QueueItem.objects.get_or_create(user=user, track=track)
                ListeningHistory.objects.get_or_create(
                    user=user,
                    track=track,
                    session_key=f"demo-session-{user.username}",
                )

        if playlists:
            playlists[0].tracks.add(*tracks[:2])
            playlists[1].tracks.add(*tracks[6:8])
