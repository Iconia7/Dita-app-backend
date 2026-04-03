from django.contrib import admin

from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import AppConfig, AppUpdate, Exam, Resource, Task


class ExamResource(resources.ModelResource):
    """Resource class for importing and exporting Exam data, specifying the model and fields to be included in the import/export process."""

    class Meta:
        model = Exam
        import_id_fields = ("course_code",)
        fields = ("course_code", "title", "date", "venue", "duration_hours")


@admin.register(Exam)
class ExamAdmin(ImportExportModelAdmin):
    """Custom admin interface for the Exam model, utilizing the ExamResource for import/export functionality and displaying key fields in the list view with search capabilities."""

    resource_class = ExamResource
    list_display = ("course_code", "title", "date", "venue")
    search_fields = ("course_code", "title")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """
    Custom admin interface for the Task model, displaying key fields in the list view with filters for completion status and due date,
    and search capabilities for the title and associated user's username.
    """

    list_display = ("title", "user", "due_date", "is_completed", "created_at")
    list_filter = ("is_completed", "due_date")
    search_fields = ("title", "user__username")


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    """Custom admin interface for the Resource model, displaying key fields in the list view with filters for resource type and search capabilities for the title and description."""

    list_display = ("title", "resource_type", "link")
    list_filter = ("resource_type",)
    search_fields = ("title", "description")


@admin.register(AppUpdate)
class AppUpdateAdmin(admin.ModelAdmin):
    """Custom admin interface for the AppUpdate model, displaying the version information and mandatory status."""

    list_display = ("version_code", "is_mandatory", "created_at")
    list_filter = ("is_mandatory",)
    search_fields = ("version_code", "release_notes")


@admin.register(AppConfig)
class AppConfigAdmin(admin.ModelAdmin):
    """Custom admin interface for the AppConfig model, allowing administrators to manage general application settings."""

    list_display = ("__str__", "is_under_maintenance", "min_version_required")

    def has_add_permission(self, request):
        """Prevent creating more than one row of AppConfig if one already exists."""
        return not AppConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """Prevent deleting the configuration."""
        return False
