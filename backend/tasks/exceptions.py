from django.core.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    if isinstance(exc, ValidationError):
        return Response({"error": exc.messages}, status=400)
    if isinstance(exc, PermissionDenied):
        return Response({"error": str(exc)}, status=403)
    return exception_handler(exc, context)
