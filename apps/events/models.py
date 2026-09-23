from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


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


class HackFestRegistration(models.Model):
    """
    Public registration model for DITA Hack Fest '26.
    Supports team and individual builders from Daystar University and external institutions.
    Enforces the 50 builder cap and assigns waitlist status when capacity is reached.
    """

    INTENT_CHOICES = [
        ("team", _("Team")),
        ("individual", _("Individual Builder")),
    ]

    STATUS_CHOICES = [
        ("confirmed", _("Confirmed")),
        ("waitlist", _("Waitlist")),
        ("cancelled", _("Cancelled")),
    ]

    event_slug = models.SlugField(max_length=50, default="hack-fest-26", db_index=True)
    registration_type = models.CharField(max_length=20, choices=INTENT_CHOICES, default="team")
    team_name = models.CharField(max_length=120, blank=True, null=True)
    team_size = models.PositiveSmallIntegerField(default=1)

    # Lead builder / individual participant
    full_name = models.CharField(max_length=150)
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=25)
    institution = models.CharField(max_length=150, default="Daystar University")
    is_daystar = models.BooleanField(default=True)
    student_id = models.CharField(max_length=50, blank=True, null=True)
    campus = models.CharField(max_length=50, blank=True, null=True)
    track_preference = models.CharField(max_length=80, blank=True, null=True)
    role_preference = models.CharField(max_length=80, blank=True, null=True)

    # Additional teammates JSON: [{"full_name": "...", "email": "...", "phone": "...", "institution": "...", "student_id": "...", "role": "..."}]
    roster_data = models.JSONField(default=list, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="confirmed", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("Hack Fest Registration")
        verbose_name_plural = _("Hack Fest Registrations")
        constraints = [
            models.UniqueConstraint(
                fields=["event_slug", "email"],
                name="unique_hackfest_event_email",
            )
        ]

    def __str__(self):
        label = self.team_name if self.registration_type == "team" and self.team_name else self.full_name
        return f"[{self.event_slug}] {label} ({self.status})"

    @property
    def display_name(self):
        if self.registration_type == "team" and self.team_name:
            return f"{self.team_name} (Lead: {self.full_name})"
        return self.full_name

    def save(self, *args, **kwargs):
        # Auto-compute confirmed builder headcount against 50 builder cap if new registration
        if not self.pk and self.status == "confirmed":
            from django.db.models import Sum

            current_headcount = (
                HackFestRegistration.objects.filter(event_slug=self.event_slug, status="confirmed")
                .aggregate(total=Sum("team_size"))["total"]
                or 0
            )
            if current_headcount + self.team_size > 50:
                self.status = "waitlist"
        super().save(*args, **kwargs)
