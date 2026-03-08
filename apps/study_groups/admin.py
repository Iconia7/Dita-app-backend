from django.contrib import admin

from .models import GroupMessage, StudyGroup


@admin.register(StudyGroup)
class StudyGroupAdmin(admin.ModelAdmin):
    """
    Custom admin interface for the StudyGroup model, displaying key fields in the list view with filters for course code and creation date, search capabilities for name, course code, creator's username, and description, and read-only fields for creation timestamp and member information.
    The member count and member list are displayed as read-only fields, providing administrators with insights into group membership
    """

    list_display = ("name", "course_code", "creator", "member_count", "created_at")
    list_filter = ("course_code", "created_at")
    search_fields = ("name", "course_code", "creator__username", "description")
    readonly_fields = ("created_at", "member_count", "member_list")

    def member_count(self, obj):
        """Calculate the number of members in the study group by counting the related members, providing a quick overview of group size in the admin interface."""
        return obj.members.count()

    member_count.short_description = "Members"

    def member_list(self, obj):
        """Generate a comma-separated list of member usernames for the study group, displaying up to 10 members and indicating if there are additional members beyond that, allowing administrators to quickly see who is in the group without needing to navigate to a separate page."""
        members = obj.members.all()[:10]
        member_names = ", ".join([m.username for m in members])
        if obj.members.count() > 10:
            member_names += f" ... (+{obj.members.count() - 10} more)"
        return member_names or "No members yet"

    member_list.short_description = "Member List"
