import posixpath
import uuid
from pathlib import PurePosixPath

from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.urls import reverse


class DatabaseMediaStorage(Storage):
    def _normalize_name(self, name):
        clean_name = posixpath.normpath(str(PurePosixPath(name).as_posix())).lstrip("/")
        return "" if clean_name == "." else clean_name

    def _open(self, name, mode="rb"):
        from .models import StoredMediaFile

        stored = StoredMediaFile.objects.get(file_key=self._normalize_name(name))
        return ContentFile(bytes(stored.content), name=stored.original_name or stored.file_key)

    def _save(self, name, content):
        from .models import StoredMediaFile

        normalized_name = self.get_available_name(self._normalize_name(name))
        content.open("rb")
        payload = content.read()
        StoredMediaFile.objects.update_or_create(
            file_key=normalized_name,
            defaults={
                "original_name": getattr(content, "name", "") or posixpath.basename(normalized_name),
                "content_type": getattr(content, "content_type", "") or "",
                "size": len(payload),
                "content": payload,
            },
        )
        return normalized_name

    def delete(self, name):
        from .models import StoredMediaFile

        StoredMediaFile.objects.filter(file_key=self._normalize_name(name)).delete()

    def exists(self, name):
        from .models import StoredMediaFile

        return StoredMediaFile.objects.filter(file_key=self._normalize_name(name)).exists()

    def size(self, name):
        from .models import StoredMediaFile

        return (
            StoredMediaFile.objects.filter(file_key=self._normalize_name(name))
            .values_list("size", flat=True)
            .first()
            or 0
        )

    def url(self, name):
        return reverse("media_file", args=[self._normalize_name(name)])

    def get_available_name(self, name, max_length=None):
        normalized_name = self._normalize_name(name)
        if not self.exists(normalized_name):
            return normalized_name

        base_path, file_name = posixpath.split(normalized_name)
        stem, dot, suffix = file_name.partition(".")
        unique_suffix = uuid.uuid4().hex[:10]
        candidate = f"{stem}-{unique_suffix}{dot}{suffix}" if dot else f"{stem}-{unique_suffix}"
        return posixpath.join(base_path, candidate) if base_path else candidate
