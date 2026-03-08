import base64
from io import BytesIO

from django.contrib import admin
from django.utils.html import format_html

import qrcode

from .models import RSVP, Announcement, Event

admin.site.register(RSVP)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """Custom admin interface for the Event model, displaying a QR code preview for attendance tracking."""

    list_display = ("title", "date", "venue", "qr_code_preview")
    readonly_fields = ("qr_code_preview",)

    def qr_code_preview(self, obj):
        """Generate a QR code preview for the event, which can be scanned for attendance tracking. The QR code encodes the event's ID."""
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
    """Custom admin interface for the Announcement model, allowing administrators to manage announcements with fields for title, message, date posted, active status, and an optional image. The list display includes the title, date posted, and active status, with filters for active status and date posted, and search functionality for the title and message fields."""

    list_display = ("title", "date_posted", "is_active")
    list_filter = ("is_active", "date_posted")
    search_fields = ("title", "message")
