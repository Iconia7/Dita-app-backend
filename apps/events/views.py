from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from .models import RSVP, Announcement, Event
from .serializers import AnnouncementSerializer, EventSerializer


class EventViewSet(viewsets.ModelViewSet):
    """ViewSet for managing events, including listing, retrieving, creating, updating, and deleting events, as well as custom actions for checking in and RSVPing to events."""

    queryset = Event.objects.all().order_by("date")
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """Override the get_queryset method to allow filtering events by attendance using query parameters."""
        attended_by = self.request.query_params.get("attended_by")
        if attended_by:
            return Event.objects.filter(checked_in_users__id=attended_by).order_by("-date")
        return Event.objects.all().order_by("date")

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def check_in(self, request, pk=None):
        """Custom action to check in a user to an event, awarding points for attendance."""
        event = self.get_object()
        user = request.user
        if event.checked_in_users.filter(id=user.id).exists():
            return Response({"message": "Already checked in!"}, status=400)
        event.checked_in_users.add(user)
        user.points += 20
        user.save()
        return Response({"message": "Check-in Successful! +20 Points", "new_points": user.points})

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def rsvp(self, request, pk=None):
        """Custom action to RSVP to an event."""
        event = self.get_object()
        user = request.user
        try:
            rsvp, created = RSVP.objects.get_or_create(user=user, event=event)
            if not created:
                rsvp.delete()
                return Response({"status": "un-rsvped", "message": "RSVP cancelled"})
            return Response({"status": "rsvped", "message": "RSVP successful"})
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class AnnouncementViewSet(viewsets.ModelViewSet):
    """ViewSet for managing announcements, including listing, retrieving, creating, updating, and deleting announcements."""

    queryset = Announcement.objects.filter(is_active=True).order_by("-date_posted")
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
