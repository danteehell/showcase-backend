import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin_url = os.getenv("ADMIN_URL", "admin/")

urlpatterns = [
    path(admin_url, admin.site.urls),
    path("api/v1/showcase/", include("showcase.urls")),
    path("api/v1/tasks/", include("tasks.urls")),
    path("api/v1/users/", include("users.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
