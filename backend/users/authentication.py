import requests
import jwt
from rest_framework import authentication, exceptions
from django.conf import settings
from .models import User

class KeycloakAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        print("=== РАБОТАЕТ НОВАЯ АВТОРИЗАЦИЯ KEYCLOAK ===") 
        
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None

        try:
            prefix, token = auth_header.split(' ')
            if prefix.lower() != 'bearer':
                raise exceptions.AuthenticationFailed('Invalid token prefix')
        except ValueError:
            raise exceptions.AuthenticationFailed('Invalid token header format')

        realm_url = settings.OIDC_AUTH.get('OIDC_ENDPOINT')
        if 'localhost' in realm_url:
            realm_url = realm_url.replace('localhost', 'host.docker.internal')

        try:
            oidc_config = requests.get(f"{realm_url}/.well-known/openid-configuration").json()
            jwks_uri = oidc_config['jwks_uri']
            if 'localhost' in jwks_uri:
                jwks_uri = jwks_uri.replace('localhost', 'host.docker.internal')
            
            jwks = requests.get(jwks_uri).json()
        except requests.exceptions.RequestException:
            raise exceptions.AuthenticationFailed('Could not connect to Keycloak')

        header = jwt.get_unverified_header(token)
        public_key = None
        for jwk in jwks['keys']:
            if jwk['kid'] == header['kid']:
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
                break

        if not public_key:
            raise exceptions.AuthenticationFailed('Public key not found')

        try:
            payload = jwt.decode(
                token, 
                public_key, 
                algorithms=['RS256'], 
                options={"verify_aud": False, "verify_iss": False},
                leeway=10
            )
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('Invalid token')

        keycloak_id = payload.get('sub')
        email = payload.get('email', '')
        username = payload.get('preferred_username', email or keycloak_id)

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'keycloak_id': keycloak_id,
                'email': email,
                'role': 'student',
            }
        )
        if not created and not user.keycloak_id:
            user.keycloak_id = keycloak_id
            user.save()

        return (user, token)