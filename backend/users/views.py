from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from .models import User

@method_decorator(ensure_csrf_cookie, name='dispatch')
class LoginView(APIView):
    permission_classes = []

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({"error": "Укажите email и пароль"}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            return Response({
                "message": "Успешный вход",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Неверная почта или пароль"}, status=status.HTTP_401_UNAUTHORIZED)


class MeView(APIView):
    def get(self, request):
        user = request.user
        data = {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "middle_name": user.middle_name,
            "role": user.role
        }

        # Подтягиваем данные по роли.
        if user.role == 'student' and hasattr(user, 'student_profile'):
            data["student_profile"] = {
                "course": user.student_profile.course,
                "specialty": user.student_profile.specialty.name if user.student_profile.specialty else None
            }
        elif user.role == 'curator' and hasattr(user, 'curator_profile'):
            data["curator_profile"] = {
                "department": user.curator_profile.department
            }

        return Response(data)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"message": "Вы вышли из системы"}, status=status.HTTP_200_OK)