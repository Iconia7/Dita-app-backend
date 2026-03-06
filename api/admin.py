from import_export import resources  # <--- THIS IS THE CORRECT ONE
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from import_export.admin import ImportExportModelAdmin
from django.utils.html import format_html
import qrcode
import base64
from io import BytesIO
from .models import (
    RSVP,
    AppConfig,
    AppUpdate,
    CommunityComment,
    CommunityPost,
    Exam,
    LostItem,
    Promotion,
    Task,
    User,
    Event,
    Payment,
    Announcement,
    Resource,
    Story,
    StudyGroup,  # Added for admin panel registration
)

admin.site.register(RSVP)


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "short_content",
        "has_image",
        "category",
        "total_likes_display",
        "created_at",
    )  # Added has_image
    list_filter = ("category", "created_at")
    search_fields = ("content", "user__username")
    readonly_fields = ("total_likes_display",)

    def short_content(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

    short_content.short_description = "Content"

    # 🟢 Helper to show if image exists
    def has_image(self, obj):
        return bool(obj.image)

    has_image.boolean = True
    has_image.short_description = "Image?"

    def total_likes_display(self, obj):
        return obj.total_likes

    total_likes_display.short_description = "Likes"


@admin.register(CommunityComment)
class CommunityCommentAdmin(admin.ModelAdmin):
    list_display = ("user", "post_preview", "text_preview", "created_at")
    search_fields = ("text", "user__username")

    def post_preview(self, obj):
        return str(obj.post)[:30] + "..."

    def text_preview(self, obj):
        return obj.text[:50] + "..."


@admin.register(LostItem)
class LostItemAdmin(admin.ModelAdmin):
    list_display = ("category", "item_name", "location", "is_resolved", "created_at")
    list_filter = ("category", "is_resolved")
    search_fields = ("item_name", "description")


@admin.register(AppUpdate)
class AppUpdateAdmin(admin.ModelAdmin):
    list_display = ("version_name", "version_code", "is_mandatory", "created_at")


class ExamResource(resources.ModelResource):
    class Meta:
        model = Exam
        import_id_fields = ("course_code",)  # Use course code to update existing rows
        fields = ("course_code", "title", "date", "venue", "duration_hours")


@admin.register(Exam)
class ExamAdmin(ImportExportModelAdmin):
    resource_class = ExamResource
    list_display = ("course_code", "title", "date", "venue")
    search_fields = ("course_code", "title")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "due_date", "is_completed", "created_at")
    list_filter = ("is_completed", "due_date")
    search_fields = ("title", "user__username")


# 1. Custom User Admin
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "admission_number",
        "program",
        "is_active_member",
        "membership_expiry",
        "points",
        "fcm_token",
    )
    list_filter = ("membership_expiry", "program", "year_of_study", "is_staff")

    fieldsets = UserAdmin.fieldsets + (
        (
            "Student Details",
            {
                "fields": (
                    "admission_number",
                    "program",
                    "year_of_study",
                    "phone_number",
                    "membership_expiry",
                    "points",
                    "fcm_token",
                )
            },
        ),
    )


# 2. Event Admin
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "date", "venue", "qr_code_preview")
    readonly_fields = ("qr_code_preview",)

    def qr_code_preview(self, obj):
        if not obj.pk:
            return "Save the event first to generate QR"

        # 1. Generate QR based on the Event ID
        qr = qrcode.QRCode(version=1, box_size=5, border=2)
        qr.add_data(str(obj.id))  # <--- This is the data the App scans
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # 2. Convert to Base64 to display in HTML
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode()

        # 3. Return HTML Image tag
        return format_html(f'<img src="data:image/png;base64,{img_str}" width="150" height="150" />')

    qr_code_preview.short_description = "Scan for Attendance"


# 3. Payment Admin
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("student", "amount", "phone_number", "status", "timestamp", "mpesa_receipt")
    list_filter = ("status", "timestamp")
    search_fields = ("student__username", "phone_number", "mpesa_receipt", "external_reference")


# 4. Announcement Admin
@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "date_posted", "is_active")
    list_filter = ("is_active", "date_posted")
    search_fields = ("title", "message")


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ("title", "action_text", "link", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("title", "message", "link")
    readonly_fields = ("created_at",)

    fieldsets = (
        (None, {"fields": ("title", "message", "image", "link", "action_text")}),
        ("Status", {"fields": ("is_active", "created_at")}),
    )


# 5. Resource Admin (NEW)
@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "resource_type", "link")
    list_filter = ("resource_type",)
    search_fields = ("title", "description")


@admin.register(AppConfig)
class AppConfigAdmin(admin.ModelAdmin):
    list_display = ("__str__", "maintenance_mode", "maintenance_title")

    # Optional: Prevent creating more than one row if one exists
    def has_add_permission(self, request):
        return not AppConfig.objects.exists()

    # Optional: Prevent deleting the configuration
    def has_delete_permission(self, request, obj=None):
        return False


# 6. Story Admin
@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ("user", "caption_preview", "has_media", "created_at", "is_expired", "likes_count", "views_count")
    list_filter = ("created_at",)
    search_fields = ("user__username", "caption")
    readonly_fields = ("created_at", "likes_count", "views_count")

    def caption_preview(self, obj):
        if not obj.caption:
            return "(No caption)"
        return (obj.caption[:50] + "...") if len(obj.caption) > 50 else obj.caption

    caption_preview.short_description = "Caption"

    def has_media(self, obj):
        return bool(obj.image or obj.video)

    has_media.boolean = True
    has_media.short_description = "Media?"

    def likes_count(self, obj):
        return obj.liked_by.count()

    likes_count.short_description = "Likes"

    def views_count(self, obj):
        return obj.viewed_by.count()

    views_count.short_description = "Views"

    def is_expired(self, obj):
        return obj.is_expired

    is_expired.boolean = True
    is_expired.short_description = "Expired?"


# 7. StudyGroup Admin
@admin.register(StudyGroup)
class StudyGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "course_code", "creator", "member_count", "created_at")
    list_filter = ("course_code", "created_at")
    search_fields = ("name", "course_code", "creator__username", "description")
    readonly_fields = ("created_at", "member_count", "member_list")

    def member_count(self, obj):
        return obj.members.count()

    member_count.short_description = "Members"

    def member_list(self, obj):
        members = obj.members.all()[:10]  # Show first 10 members
        member_names = ", ".join([m.username for m in members])
        if obj.members.count() > 10:
            member_names += f" ... (+{obj.members.count() - 10} more)"
        return member_names or "No members yet"

    member_list.short_description = "Member List"
