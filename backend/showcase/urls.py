from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import FiltersViewSet, PartnerViewSet, ProjectListAPI, ProjectViewSet

router = SimpleRouter()
router.register(r"projects-viewset", ProjectViewSet, basename="project-detail")
router.register(r"filters", FiltersViewSet, basename="filters")
router.register(r"partners", PartnerViewSet, basename="partners")

urlpatterns = [
    path("projects/", ProjectListAPI.as_view(), name="project-list"),
    path("", include(router.urls)),
]
