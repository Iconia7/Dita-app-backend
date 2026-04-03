from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission class that allows read-only access to any request, but restricts write permissions to the owner of the object.
    This permission class checks if the request method is a safe method (GET, HEAD, OPTIONS) and allows access, otherwise it checks if the object's user is the same as the request user to grant write permissions.
    """

    def has_object_permission(self, request, view, obj):
        """Check if the request method is a safe method (read-only) or if the user is the owner of the object for write permissions."""
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user
