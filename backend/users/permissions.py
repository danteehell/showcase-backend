from rest_framework import permissions


class IsAdminOrCurator(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_admin() or request.user.is_curator())
        )


class IsStudent(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.is_student()
        )
