import base64
from io import BytesIO

from django.contrib import admin
from django.utils.html import format_html
from import_export import resources
from import_export.admin import ImportExportModelAdmin

import qrcode

from .models import Announcement, Event, HackFestRegistration, RSVP

admin.site.register(RSVP)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """Custom admin interface for the Event model, displaying a QR code preview for attendance tracking."""

    list_display = ("title", "date", "venue", "qr_code_preview")
    readonly_fields = ("qr_code_preview",)

    def qr_code_preview(self, obj):
        """Generate a QR code preview for the event."""
        if not obj.pk:
            return "Save the event first to generate QR"
        qr = qrcode.QRCode(version=1, box_size=5, border=2)
        qr.add_data(str(obj.id))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode()
        return format_html(f'<img src="data:image/png;base64,{img_str}" width="150" height="150" />')

    qr_code_preview.short_description = "Scan for Attendance"


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "date_posted", "is_active")
    list_filter = ("is_active", "date_posted")
    search_fields = ("title", "message")


class HackFestRegistrationResource(resources.ModelResource):
    class Meta:
        model = HackFestRegistration
        fields = (
            "id",
            "event_slug",
            "registration_type",
            "team_name",
            "team_size",
            "full_name",
            "email",
            "phone",
            "institution",
            "is_daystar",
            "student_id",
            "campus",
            "track_preference",
            "role_preference",
            "status",
            "created_at",
        )
        export_order = fields


@admin.register(HackFestRegistration)
class HackFestRegistrationAdmin(ImportExportModelAdmin):
    resource_classes = [HackFestRegistrationResource]
    list_display = (
        "id",
        "display_name",
        "registration_type",
        "team_size",
        "institution",
        "track_preference",
        "status",
        "created_at",
    )
    list_filter = (
        "status",
        "registration_type",
        "is_daystar",
        "track_preference",
        "created_at",
    )
    search_fields = (
        "team_name",
        "full_name",
        "email",
        "phone",
        "student_id",
        "institution",
    )
    readonly_fields = ("created_at", "updated_at")
