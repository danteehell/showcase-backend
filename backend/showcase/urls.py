from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import (
    FiltersViewSet,
    PartnerViewSet,
    ProjectListAPI,
    ProjectViewSet,
    ProjectEnrollmentAPI,
)

router = SimpleRouter()
router.register(r"projects-viewset", ProjectViewSet, basename="project-detail")
router.register(r"filters", FiltersViewSet, basename="filters")
router.register(r"partners", PartnerViewSet, basename="partners")

urlpatterns = [
    path("projects/", ProjectListAPI.as_view(), name="project-list"),
    path(
        "projects/enroll/",
        ProjectEnrollmentAPI.as_view(),
        name="project-enroll",
    ),
    path("", include(router.urls)),
]