from rest_framework import views, viewsets, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Q
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError

from users.models import Specialty
from users.permissions import IsAdminOrCurator
from .models import *
from .serializers import *


class ProjectApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_student():
            return ProjectApplication.objects.filter(applicant=user).order_by('-created_at')
        return ProjectApplication.objects.all().order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(applicant=self.request.user)

    def get_permissions(self):
        if self.action in ['approve', 'reject', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrCurator()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        application = self.get_object()

        if application.status != ProjectApplication.Status.PENDING:
            return Response(
                {"error": "Можно одобрять только заявки на рассмотрении."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                project = Project.objects.create(
                    title=application.title,
                    theme=application.theme,
                    campus=application.campus,
                    location_address=application.location_address,
                    difficulty=application.difficulty,
                    partner=application.partner,
                    curator=application.curator,
                    internship=application.internship,
                    spots_remaining=application.total_spots,
                    short_description=application.short_description,
                    long_description=application.long_description,
                    is_active=True
                )

                project.specialties.set(application.specialties.all())
                project.courses.set(application.courses.all())

                if isinstance(application.tasks, list):
                    for task_text in application.tasks:
                        ProjectListItem.objects.create(project=project, type='tasks', text=task_text)
                
                if isinstance(application.technologies, list):
                    for tech_text in application.technologies:
                        ProjectListItem.objects.create(project=project, type='technologies', text=tech_text)

                application.status = ProjectApplication.Status.APPROVED
                application.save()

            return Response({
                "message": "Заявка одобрена, проект успешно создан.",
                "project_id": project.id
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"Ошибка при создании проекта: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        application = self.get_object()

        if application.status != ProjectApplication.Status.PENDING:
            return Response(
                {"error": "Можно отклонять только заявки на рассмотрении."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        reason_choice = request.data.get('rejection_reason_choice')
        reason_text = request.data.get('rejection_reason_text', '')

        if not reason_choice:
            return Response(
                {"error": "Необходимо указать причину отклонения (rejection_reason_choice)."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if reason_choice == ProjectApplication.RejectionReason.OTHER and not reason_text:
            return Response(
                {"error": "Для причины 'Другая' необходимо добавить комментарий (rejection_reason_text)."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        application.status = ProjectApplication.Status.REJECTED
        application.rejection_reason_choice = reason_choice
        application.rejection_reason_text = reason_text
        
        try:
            application.full_clean()
            application.save()
            return Response({"message": "Заявка отклонена."}, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": e.message_dict}, status=status.HTTP_400_BAD_REQUEST)


class ProjectListAPI(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        projects = Project.objects.select_related(
            "theme", "campus", "difficulty", "partner", "curator"
        ).prefetch_related(
            "specialties", "courses", "list_items",
        ).all()

        search = request.GET.get("search")
        if search:
            projects = projects.filter(
                Q(title__icontains=search) | 
                Q(short_description__icontains=search) | 
                Q(long_description__icontains=search)
            )

        theme_ids = request.GET.getlist("theme")
        if theme_ids:
            try:
                theme_ids = [int(t) for t in theme_ids if t.isdigit()]
                if theme_ids:
                    projects = projects.filter(theme_id__in=theme_ids)
            except ValueError:
                pass

        specialty_ids = request.GET.getlist("specialty")
        if specialty_ids:
            try:
                specialty_ids = [int(s) for s in specialty_ids if s.isdigit()]
                if specialty_ids:
                    projects = projects.filter(specialties__id__in=specialty_ids).distinct()
            except ValueError:
                pass

        course_ids = request.GET.getlist("course")
        if course_ids:
            try:
                course_ids = [int(c) for c in course_ids if c.isdigit()]
                if course_ids:
                    projects = projects.filter(courses__id__in=course_ids).distinct()
            except ValueError:
                pass

        difficulty_ids = request.GET.getlist("difficulty")
        if difficulty_ids:
            try:
                difficulty_ids = [int(d) for d in difficulty_ids if d.isdigit()]
                if difficulty_ids:
                    projects = projects.filter(difficulty_id__in=difficulty_ids)
            except ValueError:
                pass

        partner_ids = request.GET.getlist("partner")
        if partner_ids:
            try:
                partner_ids = [int(p) for p in partner_ids if p.isdigit()]
                if partner_ids:
                    projects = projects.filter(partner_id__in=partner_ids)
            except ValueError:
                pass

        campus_ids = request.GET.getlist("campus")
        if campus_ids:
            try:
                campus_ids = [int(c) for c in campus_ids if c.isdigit()]
                if campus_ids:
                    projects = projects.filter(campus_id__in=campus_ids)
            except ValueError:
                pass

        internship = request.GET.get("internship")
        if internship is not None:
            if internship.lower() in ["true", "1"]:
                projects = projects.filter(internship=True)
            elif internship.lower() in ["false", "0"]:
                projects = projects.filter(internship=False)

        sort = request.GET.get("sort")
        if sort == "created_at_desc":
            projects = projects.order_by("-created_at")
        elif sort == "created_at_asc":
            projects = projects.order_by("created_at")
        elif sort == "title_asc":
            projects = projects.order_by("title")
        elif sort == "title_desc":
            projects = projects.order_by("-title")
        else:
            projects = projects.order_by("-created_at")

        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 6))
        start = (page - 1) * limit
        end = start + limit
        
        total_projects = projects.count()
        projects_page = projects[start:end]

        serializer = ProjectSerializer(projects_page, many=True)
        return Response(
            {
                "data": serializer.data,
                "totalProjects": total_projects,
                "availableProjects": projects.filter(spots_remaining__gt=0).count(),
                "totalPages": (total_projects + limit - 1) // limit if total_projects > 0 else 1,
                "page": page,
            }
        )


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    lookup_field = "id"

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdminOrCurator()]
        return [AllowAny()]


class FiltersViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    queryset = FilterCategory.objects.all().prefetch_related("options")
    serializer_class = FilterCategorySerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = {cat["name"]: cat for cat in serializer.data}

        specialties = Specialty.objects.all().values("id", "code", "name")
        data["Специальность"] = {
            "id": 999,
            "name": "Специальность",
            "options": [
                {"id": s["id"], "name": f"{s['code']} - {s['name']}"}
                for s in specialties
            ],
        }

        return Response(data)


class PartnerViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({"data": serializer.data})


class ProjectEnrollmentAPI(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_student():
            return Response(
                {"error": "Только студенты могут просматривать свою запись"},
                status=status.HTTP_403_FORBIDDEN,
            )

        enrollment = ProjectEnrollment.objects.filter(
            student=request.user
        ).select_related("project").first()

        if not enrollment:
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

        if not project_id:
            return Response(
                {"error": "Необходимо указать project_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            project_id = int(project_id)
            if project_id <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return Response(
                {"error": "Некорректный ID проекта"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                project = Project.objects.select_for_update().get(id=project_id)

                if not project.is_active:
                    return Response(
                        {"error": "Проект недоступен для записи"},
                        status=status.HTTP_409_CONFLICT,
                    )

                if project.spots_remaining is None or project.spots_remaining <= 0:
                    return Response(
                        {"error": "На проекте нет свободных мест"},
                        status=status.HTTP_409_CONFLICT,
                    )

                if ProjectEnrollment.objects.filter(student=request.user).exists():
                    return Response(
                        {"error": "Вы уже записаны на проект"},
                        status=status.HTTP_409_CONFLICT,
                    )

                enrollment = ProjectEnrollment.objects.create(
                    project=project,
                    student=request.user,
                )

                project.spots_remaining -= 1
                project.save(update_fields=["spots_remaining"])

        except Project.DoesNotExist:
            return Response(
                {"error": "Проект не найден"},
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
                "enrollment_id": enrollment.id,
                "project_id": project.id,
                "project_title": project.title,
                "created_at": enrollment.created_at,
            },
            status=status.HTTP_201_CREATED,
        )