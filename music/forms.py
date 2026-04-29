from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError

from .models import (
    Album,
    Announcement,
    Artist,
    Category,
    FAQ,
    LegalPage,
    SiteSettings,
    Track,
    UserPost,
    UserProfile,
)


User = get_user_model()
MAX_IMAGE_SIZE_MB = 5
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class StyledFieldsMixin:
    field_order = ()

    def _apply_field_styles(self):
        for name, field in self.fields.items():
            css_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css_class} auth-input".strip()
            field.widget.attrs.setdefault("autocomplete", name)


class SignupForm(StyledFieldsMixin, UserCreationForm):
    field_order = ("username", "password1", "password2")

    username = forms.CharField(
        label="اسم المستخدم",
        max_length=150,
        widget=forms.TextInput(
            attrs={"placeholder": "اكتب اسم المستخدم", "autocomplete": "username"}
        ),
        help_text="استخدم حروفًا أو أرقامًا أو الرموز @ . + - _ فقط.",
    )
    password1 = forms.CharField(
        label="كلمة المرور",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"placeholder": "اختر كلمة مرور قوية", "autocomplete": "new-password"}
        ),
        help_text="يفضل أن تكون 8 أحرف أو أكثر.",
    )
    password2 = forms.CharField(
        label="تأكيد كلمة المرور",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"placeholder": "أعد كتابة كلمة المرور", "autocomplete": "new-password"}
        ),
        help_text="أعد إدخال كلمة المرور نفسها للتأكيد.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_field_styles()


class LoginForm(StyledFieldsMixin, AuthenticationForm):
    username = forms.CharField(
        label="اسم المستخدم",
        widget=forms.TextInput(attrs={"placeholder": "اسم المستخدم", "autocomplete": "username"}),
    )
    password = forms.CharField(
        label="كلمة المرور",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"placeholder": "كلمة المرور", "autocomplete": "current-password"}
        ),
    )

    error_messages = {
        "invalid_login": "تعذر تسجيل الدخول. تأكد من اسم المستخدم وكلمة المرور.",
        "inactive": "هذا الحساب غير مفعل.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_field_styles()


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("display_name", "bio", "avatar", "banner_image", "location", "website")
        widgets = {
            "display_name": forms.TextInput(attrs={"placeholder": "الاسم الظاهر"}),
            "bio": forms.Textarea(attrs={"rows": 4, "placeholder": "اكتب نبذة قصيرة عنك"}),
            "location": forms.TextInput(attrs={"placeholder": "المدينة أو الدولة"}),
            "website": forms.URLInput(attrs={"placeholder": "https://example.com"}),
        }

    def _validate_uploaded_image(self, field_name, label):
        image = self.cleaned_data.get(field_name)
        if not image:
            return image
        if not hasattr(image, "content_type"):
            return image
        if image.content_type not in ALLOWED_IMAGE_TYPES:
            raise ValidationError(f"صيغة {label} غير مدعومة.")
        if image.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
            raise ValidationError(f"حجم {label} يجب ألا يتجاوز {MAX_IMAGE_SIZE_MB}MB.")
        return image

    def clean_avatar(self):
        return self._validate_uploaded_image("avatar", "الصورة الشخصية")

    def clean_banner_image(self):
        return self._validate_uploaded_image("banner_image", "صورة الغلاف")


class UserPostForm(forms.ModelForm):
    body = forms.CharField(
        label="النص",
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 5, "placeholder": "شارك منشورًا جديدًا أو أضف أغنية من نغم"}
        ),
    )
    shared_track = forms.ModelChoiceField(
        label="مشاركة مقطع موجود",
        queryset=Track.objects.filter(is_published=True).select_related("artist").order_by("title"),
        required=False,
        empty_label="بدون مقطع مرتبط",
    )

    class Meta:
        model = UserPost
        fields = ("body", "shared_track", "image")
        widgets = {
            "body": forms.Textarea(
                attrs={"rows": 5, "placeholder": "شارك منشورًا جديدًا مع جمهورك"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        body = (cleaned_data.get("body") or "").strip()
        image = cleaned_data.get("image")
        shared_track = cleaned_data.get("shared_track")

        if not any([body, image, shared_track]):
            raise ValidationError("أضف نصًا أو صورة أو أغنية لمشاركة منشورك.")

        cleaned_data["body"] = body
        return cleaned_data

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if not image:
            return image
        if image.content_type not in ALLOWED_IMAGE_TYPES:
            raise ValidationError("صيغة الصورة غير مدعومة.")
        if image.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
            raise ValidationError(f"حجم الصورة يجب ألا يتجاوز {MAX_IMAGE_SIZE_MB}MB.")
        return image


class StaffAccountForm(StyledFieldsMixin, UserCreationForm):
    email = forms.EmailField(label="البريد الإلكتروني", required=False)
    display_name = forms.CharField(label="الاسم الظاهر", max_length=120, required=False)
    bio = forms.CharField(label="نبذة", required=False, widget=forms.Textarea(attrs={"rows": 3}))
    is_superuser = forms.BooleanField(label="منح صلاحية مدير كامل", required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_field_styles()


class QuickCategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name", "description", "cover")


class QuickArtistForm(forms.ModelForm):
    class Meta:
        model = Artist
        fields = ("name", "image", "bio", "verified")


class QuickAlbumForm(forms.ModelForm):
    class Meta:
        model = Album
        fields = ("title", "artist", "category", "cover", "description", "release_date")


class QuickTrackForm(forms.ModelForm):
    class Meta:
        model = Track
        fields = (
            "title",
            "artist",
            "album",
            "category",
            "audio_file",
            "cover",
            "description",
            "lyrics",
            "duration_seconds",
            "mood",
            "is_featured",
            "is_published",
            "allow_download",
        )


class QuickAnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ("title", "message", "link_label", "link_url", "is_active", "starts_at", "ends_at")


class QuickFAQForm(forms.ModelForm):
    class Meta:
        model = FAQ
        fields = ("question", "answer", "is_active", "sort_order")


class QuickLegalPageForm(forms.ModelForm):
    class Meta:
        model = LegalPage
        fields = (
            "title",
            "slug",
            "summary",
            "content",
            "meta_title",
            "meta_description",
            "is_published",
            "show_in_footer",
        )


class SiteBrandingForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = (
            "site_name",
            "tagline",
            "logo",
            "favicon",
            "canonical_domain",
            "analytics_code",
            "google_site_verification",
            "custom_head_code",
            "verification_file_name",
            "verification_file_content",
            "header_cta_label",
            "header_cta_url",
        )
        widgets = {
            "site_name": forms.TextInput(attrs={"placeholder": "اسم المنصة"}),
            "tagline": forms.TextInput(attrs={"placeholder": "وصف قصير يظهر تحت اسم الموقع"}),
            "canonical_domain": forms.URLInput(attrs={"placeholder": "https://example.com"}),
            "analytics_code": forms.Textarea(attrs={"rows": 3, "placeholder": "G-XXXX أو كود Analytics كامل"}),
            "google_site_verification": forms.TextInput(
                attrs={"placeholder": "ألصق قيمة content فقط أو الرمز الذي يعطيك إياه Google"}
            ),
            "custom_head_code": forms.Textarea(
                attrs={"rows": 5, "placeholder": '<meta ...> أو <script ...></script>'}
            ),
            "verification_file_name": forms.TextInput(
                attrs={"placeholder": "google1234567890abcdef.html"}
            ),
            "verification_file_content": forms.Textarea(
                attrs={"rows": 4, "placeholder": "google-site-verification: google1234567890abcdef.html"}
            ),
            "header_cta_label": forms.TextInput(attrs={"placeholder": "نص زر الهيدر"}),
            "header_cta_url": forms.TextInput(attrs={"placeholder": "/signup/ أو رابط مخصص"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css_class} auth-input".strip()
        self.fields["site_name"].label = "اسم الموقع"
        self.fields["tagline"].label = "الشعار النصي"
        self.fields["logo"].label = "الشعار"
        self.fields["favicon"].label = "الأيقونة"
        self.fields["canonical_domain"].label = "الدومين الأساسي"
        self.fields["analytics_code"].label = "Analytics code"
        self.fields["google_site_verification"].label = "Google site verification"
        self.fields["custom_head_code"].label = "Custom head code"
        self.fields["verification_file_name"].label = "اسم ملف التحقق"
        self.fields["verification_file_content"].label = "محتوى ملف التحقق"
        self.fields["header_cta_label"].label = "نص زر الهيدر"
        self.fields["header_cta_url"].label = "رابط زر الهيدر"

    def _validate_uploaded_image(self, field_name, label):
        image = self.cleaned_data.get(field_name)
        if not image:
            return image
        if not hasattr(image, "content_type"):
            return image
        if image.content_type not in ALLOWED_IMAGE_TYPES:
            raise ValidationError(f"صيغة {label} غير مدعومة.")
        if image.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
            raise ValidationError(f"حجم {label} يجب ألا يتجاوز {MAX_IMAGE_SIZE_MB}MB.")
        return image

    def clean_logo(self):
        return self._validate_uploaded_image("logo", "الشعار")

    def clean_favicon(self):
        return self._validate_uploaded_image("favicon", "الأيقونة")

    def clean_google_site_verification(self):
        value = (self.cleaned_data.get("google_site_verification") or "").strip()
        if not value:
            return ""
        if 'content="' in value:
            marker = 'content="'
            start = value.find(marker)
            if start != -1:
                start += len(marker)
                end = value.find('"', start)
                if end != -1:
                    return value[start:end].strip()
        return value

    def clean_verification_file_name(self):
        value = (self.cleaned_data.get("verification_file_name") or "").strip()
        if not value:
            return ""
        if "/" in value or "\\" in value:
            raise ValidationError("اسم ملف التحقق يجب أن يكون اسم ملف فقط بدون مسارات.")
        if not value.endswith(".html"):
            raise ValidationError("ملف التحقق يجب أن ينتهي بـ .html")
        return value
