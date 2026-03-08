from django.conf import settings
from django.db import models


class Event(models.Model):
    """Model representing an event organized by the club."""

    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateTimeField()
    venue = models.CharField(max_length=100)
    image = models.ImageField(upload_to="events/", null=True, blank=True)
    checked_in_users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="attended_events", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class RSVP(models.Model):
    """Model representing a user's RSVP to an event."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "event")


class Announcement(models.Model):
    """Model representing an announcement made by the club."""

    title = models.CharField(max_length=200)
    message = models.TextField()
    date_posted = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to="announcements/", blank=True, null=True)

    def __str__(self):
        return self.title
