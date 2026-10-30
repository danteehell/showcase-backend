from django.db import transaction
from django.db.models import Min, Max
from rest_framework import viewsets, views, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ValidationError

from .models import Task, TaskCategory, TaskAssignment
from showcase.models import Project
from .serializers import TaskListSerializer, TaskDetailSerializer
from users.permissions import IsStudent

class TaskViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Task.objects.select_related("project", "category").filter(
            status__in=[
                Task.Status.PUBLISHED,
                Task.Status.TAKEN,
                Task.Status.IN_PROGRESS,
            ]
        )

        my_tasks = self.request.query_params.get('my_tasks')
        if my_tasks == 'true' and self.request.user.is_authenticated:

            queryset = queryset.filter(assignments__student=self.request.user)

        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TaskDetailSerializer
        return TaskListSerializer

    # ЭНДПОИНТ: Взять задачу
    @action(detail=True, methods=['post'], permission_classes=[IsStudent])
    def take(self, request, pk=None):
        with transaction.atomic():
            task = Task.objects.select_for_update().filter(pk=pk).first()
            
            if not task:
                return Response({"error": "Задача не найдена"}, status=status.HTTP_404_NOT_FOUND)
                
            if task.is_full or task.status != Task.Status.PUBLISHED:
                return Response({"error": "Эта задача уже занята или недоступна"}, status=status.HTTP_400_BAD_REQUEST)
                
            # Создаем запись о том, что студент взял задачу
            TaskAssignment.objects.create(
                task=task,
                student=request.user,
                status=TaskAssignment.Status.TAKEN
            )
            
            task.filled_people += 1
            if task.is_full:
                task.status = Task.Status.TAKEN
            task.save()
            
        return Response({"status": "Успех", "message": "Вы взяли задачу"})


class TaskFiltersAPIView(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        categories = list(
            TaskCategory.objects.values('id', 'name', 'slug')
        )
        
        projects = list(
            Project.objects.filter(tasks__isnull=False).distinct().values('id', 'title')
        )
        
        active_tasks = Task.objects.filter(status=Task.Status.PUBLISHED)
        
        points = active_tasks.aggregate(
            points_min=Min('points'), points_max=Max('points'),
        )
        deadlines = active_tasks.aggregate(
            deadline_min=Min('deadline'), deadline_max=Max('deadline'),
        )
        difficulties = [choice[0] for choice in Task.Difficulty.choices]

        return Response({
            'categories': categories,
            'projects': projects,
            'points_min': float(points['points_min'] or 0),
            'points_max': float(points['points_max'] or 0),
            'deadline_min': deadlines['deadline_min'],
            'deadline_max': deadlines['deadline_max'],
            'difficulties': difficulties,
        })