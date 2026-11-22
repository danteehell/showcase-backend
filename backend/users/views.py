from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User, PartnerRepresentative
from .serializers import UserSerializer, PartnerSerializer


def get_user_queryset(user):
    queryset = User.objects.all()

    if user.is_student():
        return queryset.select_related(
            "student_profile__group",
            "student_profile__specialty",
        )

    if user.is_curator():
        return queryset.select_related(
            "curator_profile__department",
        )

    if user.is_direction_head():
        return queryset.prefetch_related(
            "headed_specialties__faculty",
        )

    if user.is_dean():
        return queryset.prefetch_related(
            "dean_of_faculties",
        )

    if user.is_partner():
        return queryset.prefetch_related(
            "partner_roles__partner",
        )

    return queryset


@method_decorator(ensure_csrf_cookie, name="dispatch")
class LoginView(APIView):
    permission_classes = []

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"error": "Укажите email и пароль"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        authenticated_user = authenticate(
            request,
            username=email,
            password=password,
        )

        if authenticated_user is None:
            return Response(
                {"error": "Неверная почта или пароль"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = get_user_queryset(authenticated_user).get(
            pk=authenticated_user.pk,
        )

        login(request, user)

        return Response(
            {
                "message": "Успешный вход",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = get_user_queryset(request.user).get(
            pk=request.user.pk,
        )

        return Response(
            {"user": UserSerializer(user).data},
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)

        return Response(
            {"message": "Вы вышли из системы"},
            status=status.HTTP_200_OK,
        )

class PartnerView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        representative = (
            PartnerRepresentative.objects
            .select_related("partner")
            .filter(user=request.user)
            .first()
        )

        if not representative:
            return Response(
                {"detail": "Партнёр не найден."},
                status=404,
            )

        serializer = PartnerSerializer(representative.partner)
        return Response(serializer.data)