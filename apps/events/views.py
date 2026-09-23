from django.db.models import Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .models import Announcement, Event, HackFestRegistration, RSVP
from .serializers import (
    AnnouncementSerializer,
    EventSerializer,
    HackFestRegistrationSerializer,
)


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


class HackFestRegistrationThrottle(AnonRateThrottle):
    rate = "30/hour"


class HackFestRegistrationView(APIView):
    """
    Public endpoint for Hack Fest '26 registrations and capacity querying.
    Accessible to all builders (Daystar students and external participants).
    """

    permission_classes = [AllowAny]
    throttle_classes = [HackFestRegistrationThrottle]

    def get(self, request, event_slug="hack-fest-26"):
        """Return live builder headcount, 50-cap status, remaining slots, and waitlist state."""
        confirmed_count = (
            HackFestRegistration.objects.filter(event_slug=event_slug, status="confirmed").aggregate(
                total=Sum("team_size")
            )["total"]
            or 0
        )
        cap = 50
        remaining = max(0, cap - confirmed_count)

        return Response({
            "event_slug": event_slug,
            "cap": cap,
            "confirmed_count": confirmed_count,
            "remaining_slots": remaining,
            "is_full": remaining == 0,
            "waitlist_active": remaining == 0,
        })

    def post(self, request, event_slug="hack-fest-26"):
        """Submit a team or individual registration for Hack Fest '26."""
        data = request.data.copy()
        data["event_slug"] = event_slug

        serializer = HackFestRegistrationSerializer(data=data)
        if serializer.is_valid():
            registration = serializer.save()
            message = (
                "Registration confirmed! Welcome to DITA Hack Fest '26."
                if registration.status == "confirmed"
                else "The 50-builder capacity has been reached. You have been placed on the priority waitlist."
            )

            return Response(
                {
                    "success": True,
                    "status": registration.status,
                    "message": message,
                    "registration_id": registration.id,
                    "team_name": registration.team_name,
                    "team_size": registration.team_size,
                    "institution": registration.institution,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )
