
from rest_framework import serializers

from users.models import Partner, Specialty, User

from .models import (
    FilterCategory,
    FilterOption,
    Project,
    ProjectApplication,
    ProjectListItem,
)


class ProjectApplicationSerializer(serializers.ModelSerializer):
    applicant_email = serializers.ReadOnlyField(source="applicant.email")

    specialties = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Specialty.objects.all(),
        required=False,
    )

    class Meta:
        model = ProjectApplication
        fields = [
            "id",
            "applicant",
            "applicant_email",
            "status",
            "rejection_reason_choice",
            "rejection_reason_text",
            "title",
            "relevance",
            "problem",
            "goal",
            "tasks",
            "expected_result",
            "specialties",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "applicant",
            "applicant_email",
            "status",
            "rejection_reason_choice",
            "rejection_reason_text",
            "created_at",
            "updated_at",
        ]


class ProjectListItemSerializer(serializers.ModelSerializer):
    type = serializers.CharField(
        source="get_type_display",
        read_only=True,
    )
    type_code = serializers.ChoiceField(
        source="type",
        choices=ProjectListItem.TYPES,
    )

    class Meta:
        model = ProjectListItem
        fields = ["type", "type_code", "text"]


class ProjectSerializer(serializers.ModelSerializer):
    theme = serializers.CharField(
        source="theme.name",
        read_only=True,
        allow_null=True,
    )
    theme_id = serializers.PrimaryKeyRelatedField(
        source="theme",
        queryset=FilterOption.objects.select_related("category").filter(
            category__name="Тематика"
        ),
        required=False,
        allow_null=True,
        write_only=True,
    )

    specialties = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="name",
    )
    specialty_ids = serializers.PrimaryKeyRelatedField(
        source="specialties",
        many=True,
        queryset=Specialty.objects.all(),
        required=False,
        write_only=True,
    )

    campus = serializers.CharField(
        source="campus.name",
        read_only=True,
        allow_null=True,
    )
    campus_id = serializers.PrimaryKeyRelatedField(
        source="campus",
        queryset=FilterOption.objects.select_related("category").filter(
            category__name="Локация"
        ),
        required=False,
        allow_null=True,
        write_only=True,
    )

    courses = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="name",
    )
    course_ids = serializers.PrimaryKeyRelatedField(
        source="courses",
        many=True,
        queryset=FilterOption.objects.select_related("category").filter(
            category__name="Курс"
        ),
        required=False,
        write_only=True,
    )

    difficulty = serializers.CharField(
        source="difficulty.name",
        read_only=True,
        allow_null=True,
    )
    difficulty_id = serializers.PrimaryKeyRelatedField(
        source="difficulty",
        queryset=FilterOption.objects.select_related("category").filter(
            category__name="Сложность"
        ),
        required=False,
        allow_null=True,
        write_only=True,
    )

    partner = serializers.CharField(
        source="partner.name",
        read_only=True,
        allow_null=True,
    )
    partner_id = serializers.PrimaryKeyRelatedField(
        source="partner",
        queryset=Partner.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )

    curator = serializers.SerializerMethodField()
    curator_id = serializers.PrimaryKeyRelatedField(
        source="curator",
        queryset=User.objects.filter(role=User.Roles.CURATOR),
        required=False,
        allow_null=True,
        write_only=True,
    )

    technologies = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "title",
            "short_description",
            "relevance",
            "problem",
            "goal",
            "tasks",
            "expected_result",
            "theme",
            "theme_id",
            "specialties",
            "specialty_ids",
            "campus",
            "campus_id",
            "location_address",
            "courses",
            "course_ids",
            "difficulty",
            "difficulty_id",
            "partner",
            "partner_id",
            "curator",
            "curator_id",
            "internship",
            "spots_remaining",
            "is_active",
            "created_at",
            "updated_at",
            "technologies",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def get_curator(self, obj):
        if obj.curator:
            return obj.curator.get_full_name()

        return None

    def get_technologies(self, obj):
        return [
            item.text
            for item in obj.list_items.all()
            if item.type == "technologies"
        ]

    def validate(self, attrs):
        errors = {}

        expected_categories = {
            "theme": "Тематика",
            "campus": "Локация",
            "difficulty": "Сложность",
        }

        for field, category_name in expected_categories.items():
            option = attrs.get(
                field,
                getattr(self.instance, field, None) if self.instance else None,
            )

            if option and option.category.name != category_name:
                errors[f"{field}_id"] = (
                    f"Выберите опцию из категории «{category_name}»."
                )

        courses = attrs.get("courses")

        if courses is None:
            courses = (
                self.instance.courses.all()
                if self.instance
                else []
            )

        if any(course.category.name != "Курс" for course in courses):
            errors["course_ids"] = (
                "Все выбранные опции должны относиться к категории «Курс»."
            )

        curator = attrs.get(
            "curator",
            getattr(self.instance, "curator", None) if self.instance else None,
        )

        if curator and curator.role != User.Roles.CURATOR:
            errors["curator_id"] = "Пользователь должен иметь роль куратора."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs


class FilterOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FilterOption
        fields = ["id", "name"]


class FilterCategorySerializer(serializers.ModelSerializer):
    options = FilterOptionSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = FilterCategory
        fields = ["id", "name", "options"]


class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = ["id", "name", "website"]
