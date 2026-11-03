from rest_framework import serializers

from .models import Task, TaskAssignment
from .permissions import available_actions


class TaskListSerializer(serializers.ModelSerializer):
    project = serializers.CharField(source="project.name", read_only=True)
    category = serializers.CharField(source="category.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "project",
            "category",
            "short_description",
            "difficulty",
            "points",
            "deadline",
            "status",
            "status_display",
            "required_people",
            "filled_people",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TaskDetailSerializer(serializers.ModelSerializer):
    project = serializers.CharField(source="project.name", read_only=True)
    category = serializers.CharField(source="category.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    free_slots = serializers.IntegerField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    can_take = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "project",
            "category",
            "short_description",
            "description",
            "difficulty",
            "points",
            "deadline",
            "start_date",
            "published_at",
            "status",
            "status_display",
            "required_people",
            "filled_people",
            "free_slots",
            "is_full",
            "required_course_min",
            "required_course_max",
            "required_specialty",
            "can_take",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_can_take(self, obj):
        from .services import check_student_matches

        user = self.context["request"].user
        if not user.is_authenticated:
            return False
        ok, _ = check_student_matches(user, obj)
        return obj.status == Task.Status.PUBLISHED and not obj.is_full and ok


class AssignmentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    revisions_left = serializers.IntegerField(read_only=True)
    can_be_returned = serializers.BooleanField(read_only=True)
    available_actions = serializers.SerializerMethodField()

    class Meta:
        model = TaskAssignment
        fields = [
            "id",
            "task",
            "student",
            "status",
            "status_display",
            "revision_count",
            "revisions_left",
            "can_be_returned",
            "available_actions",
            "taken_at",
            "started_at",
            "submitted_at",
            "completed_at",
            "removed_at",
            "removal_reason",
        ]
        read_only_fields = fields

    def get_available_actions(self, obj):
        return available_actions(obj, self.context["request"].user)


class TaskFiltersSerializer(serializers.Serializer):
    categories = serializers.ListField(child=serializers.IntegerField(), required=False)
    projects = serializers.ListField(child=serializers.IntegerField(), required=False)
    points_min = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False
    )
    points_max = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False
    )
    deadline_min = serializers.DateTimeField(required=False)
    deadline_max = serializers.DateTimeField(required=False)
    difficulties = serializers.ListField(child=serializers.CharField(), required=False)
