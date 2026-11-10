from rest_framework import views, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db.models import Q

from users.models import Specialty
from users.permissions import IsAdminOrCurator

from .models import *
from .serializers import *


class ProjectListAPI(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        projects = Project.objects.select_related(
            "theme", "campus", "difficulty", "partner", "curator"
        ).prefetch_related(
            "specialties", "courses"
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