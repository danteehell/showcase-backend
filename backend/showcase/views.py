import logging

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from rest_framework import status, views, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response

from users.models import Specialty
from users.permissions import IsAdminOrCurator

from .models import (
    FilterCategory,
    Project,
    ProjectApplication,
    ProjectEnrollment,
    ProjectListItem,
)
from .serializers import (
    FilterCategorySerializer,
    ProjectApplicationSerializer,
    ProjectSerializer,
)


logger = logging.getLogger(__name__)
User = get_user_model()


def get_project_queryset():
    return (
        Project.objects.select_related(
            "theme",
            "campus",
            "difficulty",
            "partner",
            "curator",
        )
        .prefetch_related(
            "specialties",
            "courses",
            "list_items",
        )
        .order_by("-created_at", "-pk")
    )


def has_project_management_access(user):
    return user.is_authenticated and (
        user.is_admin() or user.is_curator()
    )


def parse_positive_id_list(request, parameter):
    values = request.query_params.getlist(parameter)

    if not values:
        return []

    try:
        parsed_values = [int(value) for value in values]
    except (TypeError, ValueError):
        raise ValueError(f"Параметр «{parameter}» должен содержать целые ID.")

    if any(value <= 0 for value in parsed_values):
        raise ValueError(f"Параметр «{parameter}» должен содержать положительные ID.")

    return list(dict.fromkeys(parsed_values))


class IsStudentUser(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_student()
        )


class ProjectApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectApplicationSerializer

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return ProjectApplication.objects.none()

        queryset = ProjectApplication.objects.select_related("applicant")

        if user.is_admin() or user.is_curator():
            return queryset.order_by("-created_at")

        if user.is_student():
            return queryset.filter(applicant=user).order_by("-created_at")

        return ProjectApplication.objects.none()

    def get_permissions(self):
        if self.action in {
            "approve",
            "reject",
            "update",
            "partial_update",
            "destroy",
        }:
            return [IsAdminOrCurator()]

        if self.action == "create":
            return [IsStudentUser()]

        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(applicant=self.request.user)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        application = self.get_object()

        try:
            with transaction.atomic():
                application = (
                    self.get_queryset()
                    .select_for_update()
                    .get(pk=application.pk)
                )

                if application.status != ProjectApplication.Status.PENDING:
                    return Response(
                        {"error": "Можно одобрять только заявки на рассмотрении."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                project = Project.objects.create(
                    title=application.title,
                    short_description=application.relevance[:150],
                    relevance=application.relevance,
                    problem=application.problem,
                    goal=application.goal,
                    tasks=application.tasks,
                    expected_result=application.expected_result,
                    spots_remaining=0,
                    is_active=True,
                )

                project.specialties.set(application.specialties.all())

                if application.tasks:
                    ProjectListItem.objects.create(
                        project=project,
                        type="tasks",
                        text=application.tasks,
                    )

                application.status = ProjectApplication.Status.APPROVED
                application.save(update_fields=["status", "updated_at"])

            return Response(
                {
                    "message": "Заявка одобрена, проект создан.",
                    "project_id": project.pk,
                },
                status=status.HTTP_200_OK,
            )
        except ProjectApplication.DoesNotExist:
            return Response(
                {"error": "Заявка не найдена."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception:
            logger.exception(
                "Не удалось одобрить заявку на проект: application_id=%s",
                application.pk,
            )
            return Response(
                {"error": "Не удалось одобрить заявку."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        application = self.get_object()
        reason_choice = request.data.get("rejection_reason_choice")
        reason_text = request.data.get("rejection_reason_text", "")

        if reason_choice not in ProjectApplication.RejectionReason.values:
            return Response(
                {"error": "Укажите корректную категорию отклонения."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(reason_text, str):
            return Response(
                {"error": "Комментарий к отклонению должен быть строкой."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason_text = reason_text.strip()

        if (
            reason_choice == ProjectApplication.RejectionReason.OTHER
            and not reason_text
        ):
            return Response(
                {
                    "error": "Для причины 'Другая' необходимо добавить комментарий (rejection_reason_text)."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                application = (
                    self.get_queryset()
                    .select_for_update()
                    .get(pk=application.pk)
                )

                if application.status != ProjectApplication.Status.PENDING:
                    return Response(
                        {"error": "Можно отклонять только заявки на рассмотрении."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                application.status = ProjectApplication.Status.REJECTED
                application.rejection_reason_choice = reason_choice
                application.rejection_reason_text = reason_text or None
                application.full_clean()
                application.save(
                    update_fields=[
                        "status",
                        "rejection_reason_choice",
                        "rejection_reason_text",
                        "updated_at",
                    ]
                )

            return Response(
                {"message": "Заявка отклонена."},
                status=status.HTTP_200_OK,
            )
        except ProjectApplication.DoesNotExist:
            return Response(
                {"error": "Заявка не найдена."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except DjangoValidationError as exc:
            return Response(
                {"error": getattr(exc, "message_dict", exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.exception(
                "Не удалось отклонить заявку на проект: application_id=%s",
                application.pk,
            )
            return Response(
                {"error": "Не удалось отклонить заявку."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ProjectListAPI(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        projects = get_project_queryset()

        if not has_project_management_access(request.user):
            projects = projects.filter(is_active=True)

        search = request.query_params.get("search", "").strip()

        if len(search) > 200:
            return Response(
                {"error": "Поисковый запрос не должен превышать 200 символов."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if search:
            projects = projects.filter(
                Q(title__icontains=search)
                | Q(short_description__icontains=search)
                | Q(relevance__icontains=search)
                | Q(problem__icontains=search)
                | Q(goal__icontains=search)
                | Q(tasks__icontains=search)
                | Q(expected_result__icontains=search)
                | Q(theme__name__icontains=search)
                | Q(partner__name__icontains=search)
            )

        filter_fields = {
            "theme": "theme_id",
            "specialty": "specialties__id",
            "course": "courses__id",
            "difficulty": "difficulty_id",
            "partner": "partner_id",
            "campus": "campus_id",
        }

        try:
            for parameter, field in filter_fields.items():
                values = parse_positive_id_list(request, parameter)

                if values:
                    projects = projects.filter(**{f"{field}__in": values})
                    if parameter in {"specialty", "course"}:
                        projects = projects.distinct()
        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        internship = request.query_params.get("internship")

        if internship is not None:
            internship_value = internship.lower()

            if internship_value in {"true", "1"}:
                projects = projects.filter(internship=True)
            elif internship_value in {"false", "0"}:
                projects = projects.filter(internship=False)
            else:
                return Response(
                    {"error": "Параметр «internship» должен быть true или false."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        sort_options = {
            "created_at_desc": ("-created_at", "-pk"),
            "created_at_asc": ("created_at", "pk"),
            "title_asc": ("title", "pk"),
            "title_desc": ("-title", "-pk"),
        }
        sort = request.query_params.get("sort", "created_at_desc")

        if sort not in sort_options:
            return Response(
                {"error": "Некорректный параметр сортировки."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        projects = projects.order_by(*sort_options[sort])

        try:
            page = int(request.query_params.get("page", 1))
            limit = int(request.query_params.get("limit", 6))
        except (TypeError, ValueError):
            return Response(
                {"error": "Параметры page и limit должны быть целыми числами."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if page < 1:
            return Response(
                {"error": "Параметр page должен быть положительным числом."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not 1 <= limit <= 100:
            return Response(
                {"error": "Параметр limit должен быть от 1 до 100."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        total_projects = projects.count()
        available_projects = projects.filter(
            is_active=True,
            spots_remaining__gt=0,
        ).count()
        start = (page - 1) * limit
        projects_page = projects[start : start + limit]

        serializer = ProjectSerializer(projects_page, many=True)

        return Response(
            {
                "data": serializer.data,
                "totalProjects": total_projects,
                "availableProjects": available_projects,
                "totalPages": max((total_projects + limit - 1) // limit, 1),
                "page": page,
            },
            status=status.HTTP_200_OK,
        )


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    lookup_field = "id"

    def get_queryset(self):
        queryset = get_project_queryset()

        if has_project_management_access(self.request.user):
            return queryset

        return queryset.filter(is_active=True)

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAdminOrCurator()]

        return [AllowAny()]


class FiltersViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    queryset = FilterCategory.objects.prefetch_related("options").order_by("name")
    serializer_class = FilterCategorySerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = {category["name"]: category for category in serializer.data}

        specialties = Specialty.objects.order_by("code").values(
            "id",
            "code",
            "name",
        )
        data["Специальность"] = {
            "id": 999,
            "name": "Специальность",
            "options": [
                {
                    "id": specialty["id"],
                    "name": f"{specialty['code']} - {specialty['name']}",
                }
                for specialty in specialties
            ],
        }

        return Response(data, status=status.HTTP_200_OK)


class ProjectEnrollmentAPI(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_student():
            return Response(
                {"error": "Только студенты могут просматривать свою запись"},
                status=status.HTTP_403_FORBIDDEN,
            )

        enrollment = (
            ProjectEnrollment.objects.filter(student=request.user)
            .select_related(
                "project",
                "project__theme",
                "project__campus",
                "project__difficulty",
                "project__partner",
                "project__curator",
            )
            .prefetch_related(
                "project__specialties",
                "project__courses",
                "project__list_items",
            )
            .order_by("-created_at", "-pk")
            .first()
        )

        if enrollment is None:
            return Response(
                {"error": "Вы не записаны ни на один проект"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ProjectSerializer(enrollment.project)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if not request.user.is_student():
            return Response(
                {"error": "Только студенты могут записываться на проекты"},
                status=status.HTTP_403_FORBIDDEN,
            )

        project_id = request.data.get("project_id")

        if isinstance(project_id, bool) or project_id in (None, ""):
            return Response(
                {"error": "Необходимо указать корректный project_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            project_id = int(project_id)
        except (TypeError, ValueError):
            return Response(
                {"error": "Некорректный ID проекта"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if project_id <= 0:
            return Response(
                {"error": "Некорректный ID проекта"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                student = User.objects.select_for_update().get(
                    pk=request.user.pk,
                )

                if not student.is_student():
                    return Response(
                        {"error": "Только студенты могут записываться на проекты"},
                        status=status.HTTP_403_FORBIDDEN,
                    )

                if ProjectEnrollment.objects.filter(student=student).exists():
                    return Response(
                        {"error": "Вы уже записаны на проект"},
                        status=status.HTTP_409_CONFLICT,
                    )

                project = Project.objects.select_for_update().get(pk=project_id)

                if not project.is_active:
                    return Response(
                        {"error": "Проект недоступен для записи"},
                        status=status.HTTP_409_CONFLICT,
                    )

                if project.spots_remaining <= 0:
                    return Response(
                        {"error": "На проекте нет свободных мест"},
                        status=status.HTTP_409_CONFLICT,
                    )

                enrollment = ProjectEnrollment.objects.create(
                    project=project,
                    student=student,
                )

                project.spots_remaining -= 1
                project.save(update_fields=["spots_remaining", "updated_at"])

        except Project.DoesNotExist:
            return Response(
                {"error": "Проект не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except User.DoesNotExist:
            return Response(
                {"error": "Пользователь не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except IntegrityError:
            return Response(
                {"error": "Вы уже записаны на проект"},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                "message": "Вы успешно записались на проект",
                "enrollment_id": enrollment.pk,
                "project_id": project.pk,
                "project_title": project.title,
                "created_at": enrollment.created_at,
            },
            status=status.HTTP_201_CREATED,
        )
