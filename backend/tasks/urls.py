from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import TaskFiltersAPIView, TaskViewSet

router = SimpleRouter()
router.register(r"", TaskViewSet, basename="task")

urlpatterns = [
    path("filters/", TaskFiltersAPIView.as_view(), name="task-filters"),
] + router.urls
