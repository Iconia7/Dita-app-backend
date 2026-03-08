from django.shortcuts import render
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import GroupMessage, StudyGroup
from .serializers import GroupMessageSerializer, StudyGroupSerializer


class StudyGroupViewSet(viewsets.ModelViewSet):
    """ViewSet for managing study groups, including listing, retrieving, creating, updating, and deleting study groups, as well as custom actions for joining, leaving, and retrieving messages for a study group."""

    queryset = StudyGroup.objects.all()
    serializer_class = StudyGroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "course_code", "description"]
    ordering_fields = ["created_at", "name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Override the get_queryset method to annotate each study group with the member count and whether the current user is a member of the group, allowing for efficient retrieval of this information in the API responses."""
        from django.db.models import Count, Exists, OuterRef

        user = self.request.user
        return StudyGroup.objects.annotate(
            is_member=Exists(StudyGroup.objects.filter(id=OuterRef("pk"), members=user)),
            member_count=Count("members"),
        )

    def perform_create(self, serializer):
        """Override the perform_create method to automatically set the creator of the study group to the currently authenticated user and add them as a member of the group upon creation."""
        group = serializer.save(creator=self.request.user)
        group.members.add(self.request.user)

    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        """Custom action to allow a user to join a study group, adding them to the group's members and returning a response indicating the status of the operation."""
        self.get_object().members.add(request.user)
        return Response({"status": "joined"})

    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        """Custom action to allow a user to leave a study group, removing their membership from the group and returning a response indicating the status of the operation."""
        self.get_object().members.remove(request.user)
        return Response({"status": "left"})

    @action(detail=True, methods=["get"])
    def messages(self, request, pk=None):
        """Custom action to retrieve all messages for a specific study group, allowing clients to fetch the chat history associated with the group."""
        group = self.get_object()
        serializer = GroupMessageSerializer(group.messages.all(), many=True)
        return Response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def group_landing_page(request, group_id):
    """
    View function for rendering the landing page of a study group, displaying group details and providing links to download the Dita app for both Android and iOS platforms.
    The view checks if the specified study group exists and renders the appropriate template based on the existence of the group.
    """
    try:
        group = StudyGroup.objects.get(id=group_id)
        context = {
            "group": group,
            "app_download_url": "https://play.google.com/store/apps/details?id=com.dita.mobile",
            "app_store_url": "https://apps.apple.com/app/dita/id123456789",
        }
        return render(request, "api/group_landing.html", context)
    except StudyGroup.DoesNotExist:
        return render(request, "api/group_not_found.html", status=404)
