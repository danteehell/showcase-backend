from rest_framework import views, viewsets
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework import status
from django.db import transaction
from django.db.models import Count

from .models import *
from .serializers import *
from users.permissions import IsAdminOrCurator, IsStudent

class ProjectListAPI(views.APIView):
    permission_classes = [AllowAny]
    def get(self, request, format=None):
        projects = Project.objects.all()

        search = request.GET.get('search')
        if search:
            projects = projects.filter(title__icontains=search)

        theme_ids = request.GET.getlist('theme')
        if theme_ids:
            theme_ids = [int(t) for t in theme_ids]
            projects = projects.filter(theme_id__in=theme_ids)

        difficulty_ids = request.GET.getlist('difficulty')
        if difficulty_ids:
            difficulty_ids = [int(d) for d in difficulty_ids]
            projects = projects.filter(difficulty_id__in=difficulty_ids)

        partner_ids = request.GET.getlist('partner')
        if partner_ids:
            partner_ids = [int(p) for p in partner_ids]
            projects = projects.filter(partner_id__in=partner_ids)

        campus_ids = request.GET.getlist('campus')
        if campus_ids:
            campus_ids = [int(c) for c in campus_ids]
            projects = projects.filter(campus__id__in=campus_ids)

        internship = request.GET.get('internship')
        if internship is not None:
            if internship.lower() in ['true', '1']:
                projects = projects.filter(internship=True)
            elif internship.lower() in ['false', '0']:
                projects = projects.filter(internship=False)

        sort = request.GET.get('sort')
        if sort == 'created_at_desc':
            projects = projects.order_by('-created_at')
        elif sort == 'created_at_asc':
            projects = projects.order_by('created_at')
        elif sort == 'title_asc':
            projects = projects.order_by('title')
        elif sort == 'title_desc':
            projects = projects.order_by('-title')

        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 10))
        start = (page - 1) * limit
        end = start + limit
        total_projects = projects.count()
        projects_page = projects[start:end]

        serializer = ProjectSerializer(projects_page, many=True)
        return Response({
            'data': serializer.data,
            'totalProjects': total_projects,
            'availableProjects': projects.filter(spots_remaining__gt=0).count(),
            'totalPages': (total_projects + limit - 1) // limit,
            'page': page,
        })


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    lookup_field = 'id'

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrCurator()]
        return [AllowAny()]
    
    @action(detail=True, methods=['post'], permission_classes=[IsStudent])
    # TODO: затестить
    def enroll(self, request, pk=None):
        with transaction.atomic():
            project = Project.objects.select_for_update().filter(pk=pk).first()
            
            if not project:
                return Response({"error": "Проект не найден"}, status=status.HTTP_404_NOT_FOUND)
                
            if project.spots_remaining <= 0:
                return Response({"error": "Свободных мест больше нет"}, status=status.HTTP_400_BAD_REQUEST)
                
            if ProjectEnrollment.objects.filter(project=project, student=request.user).exists():
                return Response({"error": "Вы уже записаны на этот проект"}, status=status.HTTP_400_BAD_REQUEST)
            ProjectEnrollment.objects.create(project=project, student=request.user)
            project.spots_remaining -= 1
            project.save()
            
        return Response({"status": "Успех", "message": "Вы записались на проект"})

    # Проекты студента
    @action(detail=False, methods=['get'], permission_classes=[IsStudent])
    def my_projects(self, request):
        enrollments = ProjectEnrollment.objects.filter(student=request.user).select_related('project')
        projects = [e.project for e in enrollments]
        serializer = self.get_serializer(projects, many=True)
        return Response(serializer.data)


class FiltersViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    queryset = FilterCategory.objects.all().prefetch_related('options')
    serializer_class = FilterCategorySerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = {cat['name']: cat for cat in serializer.data}
        return Response(data)


class PartnerViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({"data": serializer.data})
    