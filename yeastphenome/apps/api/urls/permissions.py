from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsStaffOrSuperUser(BasePermission):
    """Allows access to staff (admin) or superuser."""

    def has_permission(self, request, view):

        if request.user.is_staff or request.user.is_superuser:
            return True

        return request.method in SAFE_METHODS


class AllowAnyGet(BasePermission):
    """Allows an anonymous user access for GET requests only."""

    def has_permission(self, request, view):

        if request.user.is_anonymous and request.method == "GET":
            return True

        if request.user.is_staff or request.user.is_superuser:
            return True

        return request.method in SAFE_METHODS
