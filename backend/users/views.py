import os
import requests
import jwt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from .models import User


class LoginView(APIView):
    permission_classes = []

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {"error": "Укажите username и password"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        realm_url = settings.OIDC_AUTH.get('OIDC_ENDPOINT') or 'http://host.docker.internal:8080/realms/mospolytech'
        if 'localhost' in realm_url:
            realm_url = realm_url.replace('localhost', 'host.docker.internal')
            
        token_url = f"{realm_url}/protocol/openid-connect/token"

        payload = {
            'client_id': os.getenv('KEYCLOAK_CLIENT_ID', 'showcase'),
            'grant_type': 'password',
            'username': username,
            'password': password,
            'client_secret': os.getenv('KEYCLOAK_CLIENT_SECRET')
        }

        try:
            response = requests.post(token_url, data=payload)
            response_data = response.json()

            if response.status_code == 200:
                access_token = response_data.get('access_token')
                
                decoded = jwt.decode(access_token, options={"verify_signature": False})
                
                user, created = User.objects.get_or_create(
                    username=decoded.get('preferred_username'),
                    defaults={
                        'keycloak_id': decoded.get('sub'),
                        'email': decoded.get('email', ''),
                        'first_name': decoded.get('given_name', ''),
                        'last_name': decoded.get('family_name', ''),
                        'role': 'student'
                    }
                )
                
                return Response({
                    "access_token": access_token,
                    "refresh_token": response_data.get('refresh_token'),
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "role": user.role
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": "Неверный логин или пароль", "details": response_data}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
        except requests.exceptions.RequestException:
            return Response(
                {"error": "Сервер авторизации недоступен"}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role
        })

class LogoutView(APIView):
    permission_classes = []

    def post(self, request):
        refresh_token = request.data.get('refresh_token')

        if not refresh_token:
            return Response(
                {"error": "Требуется refresh_token"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        realm_url = settings.OIDC_AUTH.get('OIDC_ENDPOINT') or 'http://host.docker.internal:8080/realms/mospolytech'
        if 'localhost' in realm_url:
            realm_url = realm_url.replace('localhost', 'host.docker.internal')
            
        logout_url = f"{realm_url}/protocol/openid-connect/logout"

        payload = {
            'client_id': os.getenv('KEYCLOAK_CLIENT_ID', 'showcase'),
            'client_secret': os.getenv('KEYCLOAK_CLIENT_SECRET'),
            'refresh_token': refresh_token
        }

        try:
            response = requests.post(logout_url, data=payload)
            if response.status_code in [200, 204]:
                return Response({"message": "Вы успешно вышли из системы"}, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": "Ошибка при выходе из Keycloak", "details": response.text}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except requests.exceptions.RequestException:
            return Response(
                {"error": "Сервер авторизации недоступен"}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )