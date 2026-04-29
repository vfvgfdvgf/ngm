from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import include, path

from music.forms import LoginForm

urlpatterns = [
    # 🔐 رابط الأدمن الجديد
    path('login_adminnn/', admin.site.urls),

    # 👤 تسجيل الدخول
    path(
        'login/',
        auth_views.LoginView.as_view(
            authentication_form=LoginForm,
            redirect_authenticated_user=True,
            template_name='registration/login.html',
        ),
        name='login',
    ),

    # 🎵 روابط التطبيق
    path('', include('music.urls')),
]

# 📁 ملفات الميديا في وضع التطوير
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)