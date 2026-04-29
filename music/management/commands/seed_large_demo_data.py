import random
from datetime import date, timedelta

from django.db import transaction

from music.management.commands.seed_demo_data import Command as SeedDemoCommand
from music.models import (
    Album,
    Artist,
    Category,
    ListeningHistory,
    Playlist,
    QueueItem,
    Track,
    TrackComment,
    UserPost,
    UserProfile,
)


class Command(SeedDemoCommand):
    help = "Seed large-scale demo data for performance and long-page testing."

    # This command inherits internet-backed image generation from seed_demo_data.

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--scale",
            type=int,
            default=3,
            help="Scale factor for generated data. Default is 3.",
        )

    def handle(self, *args, **options):
        self.scale = max(1, options["scale"])
        with transaction.atomic():
            if options["reset"]:
                self._reset_demo_data()
                self._reset_large_demo_data()

            self.password = "DemoPass123!"
            self.user_model = self.user_model if hasattr(self, "user_model") else None

            users = self._create_users()
            self._create_site_content()
            self._create_large_profiles(users)
            categories = self._create_large_categories()
            artists = self._create_large_artists(users)
            albums = self._create_large_albums(artists, categories)
            tracks = self._create_large_tracks(artists, categories, albums)
            playlists = self._create_large_playlists(users, tracks)
            self._create_large_posts(users)
            self._create_large_social_activity(users, artists, tracks, playlists)

        self.stdout.write(
            self.style.SUCCESS(
                f"Large demo data created successfully with scale={self.scale}."
            )
        )
        self.stdout.write(
            f"Created totals: {Category.objects.count()} categories, "
            f"{Artist.objects.count()} artists, {Album.objects.count()} albums, "
            f"{Track.objects.count()} tracks, {Playlist.objects.count()} playlists."
        )

    def _reset_large_demo_data(self):
        Track.objects.filter(title__startswith="Load ").delete()
        Album.objects.filter(title__startswith="Load ").delete()
        Artist.objects.filter(name__startswith="Load ").delete()
        Category.objects.filter(name__startswith="Load ").delete()
        Playlist.objects.filter(name__startswith="Load ").delete()
        UserPost.objects.filter(body__startswith="Load ").delete()

    def _create_large_profiles(self, users):
        cities = ["Riyadh", "Jeddah", "Dammam", "Makkah", "Madinah", "Taif", "Abha"]
        for index in range(1, 1 + (self.scale * 8)):
            username = f"load_user_{index:02d}"
            user, created = self.user_model.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@example.com"},
            )
            if created or not user.check_password(self.password):
                user.set_password(self.password)
                user.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.display_name = f"مستخدم تحميل {index}"
            profile.bio = f"حساب بيانات كبيرة رقم {index} لاختبار الأداء والتصفح الطويل."
            profile.location = cities[index % len(cities)]
            if not profile.avatar:
                profile.avatar.save(
                    f"{username}-avatar.png",
                    self._image_file("avatar", username),
                    save=False,
                )
            profile.save()
            users[username] = user

    def _create_large_categories(self):
        base_names = ["هدوء", "تركيز", "قصص", "محاضرات", "أطفال", "تأمل", "روتين", "مساء"]
        categories = list(Category.objects.filter(name__startswith="Demo "))
        for index in range(1, 1 + (self.scale * 10)):
            name = f"Load {base_names[index % len(base_names)]} {index}"
            category, _ = Category.objects.get_or_create(
                name=name,
                defaults={"description": f"تصنيف كبير رقم {index} لاختبار فهارس الموقع."},
            )
            if not category.cover:
                category.cover.save(
                    f"load-category-{index}.png",
                    self._image_file("category", f"load-{index}"),
                    save=False,
                )
            category.save()
            categories.append(category)
        return categories

    def _create_large_artists(self, users):
        artists = list(Artist.objects.filter(name__startswith="Demo "))
        follower_pool = list(users.values())
        for index in range(1, 1 + (self.scale * 14)):
            artist, _ = Artist.objects.get_or_create(
                name=f"Load Artist {index}",
                defaults={
                    "bio": f"فنان كبير رقم {index} لاختبار كثافة النتائج والصفحات.",
                    "verified": index % 5 == 0,
                },
            )
            artist.bio = f"فنان كبير رقم {index} لاختبار كثافة النتائج والصفحات."
            artist.verified = index % 5 == 0
            if not artist.image:
                artist.image.save(
                    f"load-artist-{index}.png",
                    self._image_file("artist", f"load-{index}"),
                    save=False,
                )
            artist.save()
            artist.followers.set(random.sample(follower_pool, k=min(len(follower_pool), 4 + (index % 6))))
            artists.append(artist)
        return artists

    def _create_large_albums(self, artists, categories):
        albums = list(Album.objects.filter(title__startswith="Demo "))
        for index in range(1, 1 + (self.scale * 24)):
            artist = artists[index % len(artists)]
            category = categories[index % len(categories)]
            album, _ = Album.objects.get_or_create(
                title=f"Load Album {index}",
                defaults={
                    "artist": artist,
                    "category": category,
                    "description": f"ألبوم كبير رقم {index}.",
                    "release_date": date.today() - timedelta(days=index),
                },
            )
            album.artist = artist
            album.category = category
            album.description = f"ألبوم كبير رقم {index} لتجربة القوائم الطويلة."
            album.release_date = date.today() - timedelta(days=index)
            if not album.cover:
                album.cover.save(
                    f"load-album-{index}.png",
                    self._image_file("album", f"load-{index}"),
                    save=False,
                )
            album.save()
            albums.append(album)
        return albums

    def _create_large_tracks(self, artists, categories, albums):
        tracks = list(Track.objects.filter(title__startswith="Demo "))
        moods = [choice[0] for choice in Track.MOOD_CHOICES]
        total = self.scale * 80
        for index in range(1, total + 1):
            artist = artists[index % len(artists)]
            category = categories[index % len(categories)]
            album = albums[index % len(albums)]
            track, _ = Track.objects.get_or_create(
                title=f"Load Track {index}",
                defaults={
                    "artist": artist,
                    "album": album,
                    "category": category,
                    "description": f"مقطع كبير رقم {index} لتجربة الأداء والفلترة والبحث.",
                    "lyrics": f"كلمات طويلة تجريبية للمقطع {index}.",
                    "duration_seconds": 60 + ((index % 12) * 18),
                    "mood": moods[index % len(moods)],
                    "views": 100 + index * 9,
                    "is_featured": index % 11 == 0,
                    "is_published": True,
                    "allow_download": index % 3 == 0,
                },
            )
            track.artist = artist
            track.album = album
            track.category = category
            track.description = f"مقطع كبير رقم {index} لتجربة الأداء والفلترة والبحث."
            track.lyrics = f"هذا نص طويل تجريبي للمقطع {index} لاختبار صفحات التفاصيل الطويلة."
            track.duration_seconds = 60 + ((index % 12) * 18)
            track.mood = moods[index % len(moods)]
            track.views = 100 + index * 9
            track.is_featured = index % 11 == 0
            track.is_published = True
            track.allow_download = index % 3 == 0
            if not track.audio_file:
                track.audio_file.save(
                    f"load-track-{index}.wav",
                    self._audio_file(f"load-track-{index}", seconds=2, frequency=280 + (index % 20) * 12),
                    save=False,
                )
            if not track.cover:
                track.cover.save(
                    f"load-track-{index}.png",
                    self._image_file("track", f"load-{index}"),
                    save=False,
                )
            track.save()
            tracks.append(track)
        return tracks

    def _create_large_playlists(self, users, tracks):
        playlists = list(Playlist.objects.filter(name__startswith="Demo "))
        user_values = list(users.values())
        for index in range(1, 1 + (self.scale * 18)):
            owner = user_values[index % len(user_values)]
            playlist, _ = Playlist.objects.get_or_create(
                name=f"Load Playlist {index}",
                user=owner,
                defaults={
                    "description": f"قائمة كبيرة رقم {index} لاختبار صفحة القوائم.",
                    "is_public": index % 4 != 0,
                },
            )
            playlist.description = f"قائمة كبيرة رقم {index} لاختبار صفحة القوائم."
            playlist.is_public = index % 4 != 0
            if not playlist.cover:
                playlist.cover.save(
                    f"load-playlist-{index}.png",
                    self._image_file("playlist", f"load-{index}"),
                    save=False,
                )
            playlist.save()
            start = (index * 3) % max(1, len(tracks) - 12)
            playlist.tracks.set(tracks[start : start + 12])
            playlists.append(playlist)
        return playlists

    def _create_large_posts(self, users):
        user_values = list(users.values())
        for index in range(1, 1 + (self.scale * 20)):
            user = user_values[index % len(user_values)]
            body = f"Load منشور طويل رقم {index} لاختبار صفحة المجتمع والتمرير والبطاقات الكثيفة."
            post, _ = UserPost.objects.get_or_create(
                user=user,
                body=body,
                defaults={"is_published": True},
            )
            post.is_published = True
            if index % 3 == 0 and not post.image:
                post.image.save(
                    f"load-post-{index}.png",
                    self._image_file("post", f"load-{index}"),
                    save=False,
                )
            post.save()

    def _create_large_social_activity(self, users, artists, tracks, playlists):
        user_values = list(users.values())
        sample_users = user_values[: min(len(user_values), 12)]

        for index, track in enumerate(tracks):
            like_count = min(len(sample_users), 2 + (index % max(2, len(sample_users))))
            save_count = min(len(sample_users), 1 + ((index * 2) % max(2, len(sample_users))))
            track.likes.set(sample_users[:like_count])
            track.saved_by.set(sample_users[-save_count:])

            for comment_index, user in enumerate(sample_users[: min(4, len(sample_users))], start=1):
                TrackComment.objects.get_or_create(
                    track=track,
                    user=user,
                    body=f"تعليق تحميل {comment_index} على {track.title} لتجربة كثافة التعليقات.",
                    defaults={"is_visible": True},
                )

        for user in sample_users:
            for track in random.sample(tracks, k=min(14, len(tracks))):
                QueueItem.objects.get_or_create(user=user, track=track)
                ListeningHistory.objects.get_or_create(
                    user=user,
                    track=track,
                    session_key=f"load-session-{user.username}",
                )

        for artist in artists[: min(len(artists), self.scale * 10)]:
            artist.followers.set(random.sample(sample_users, k=min(len(sample_users), 5)))

        if playlists:
            for playlist in playlists[: min(len(playlists), self.scale * 8)]:
                extra_sample = random.sample(tracks, k=min(16, len(tracks)))
                playlist.tracks.add(*extra_sample)
