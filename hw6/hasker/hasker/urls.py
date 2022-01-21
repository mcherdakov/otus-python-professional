from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from django.views.generic import RedirectView


urlpatterns = [
    path('', RedirectView.as_view(url='questions/')),
    path('admin/', admin.site.urls),
    path('questions/', include('questions.urls'), name='questions'),
    path('users/', include('users.urls'), name='users'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
