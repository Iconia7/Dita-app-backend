from django.contrib import admin
from .models import CommunityComment, CommunityPost, LostItem, Story, StoryComment


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    """
    Custom admin interface for the CommunityPost model, allowing administrators to manage community posts with fields for
    user, content, image, category, likes, and creation date.
    """

    list_display = ("user", "short_content", "has_image", "category", "total_likes_display", "created_at")
    list_filter = ("category", "created_at")
    search_fields = ("content", "user__username")
    readonly_fields = ("total_likes_display",)

    def short_content(self, obj):
        """
        Helper method to display a shortened version of the post content in the admin list view.
        If the content exceeds 50 characters, it truncates the content and appends an ellipsis.
        """
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

    short_content.short_description = "Content"

    def has_image(self, obj):
        """
        Helper method to indicate whether the post has an associated image.
        This method returns a boolean value that is displayed as a boolean icon in the admin list view.
        """
        return bool(obj.image)

    has_image.boolean = True
    has_image.short_description = "Image?"

    def total_likes_display(self, obj):
        """
        Helper method to display the total number of likes for the post in the admin list view.
        This method retrieves the total_likes property from the CommunityPost model and returns it for display.
        """
        return obj.total_likes

    total_likes_display.short_description = "Likes"


@admin.register(CommunityComment)
class CommunityCommentAdmin(admin.ModelAdmin):
    """
    Custom admin interface for the CommunityComment model, allowing administrators to manage comments on community posts with fields for user, post preview, comment text preview, and creation date.
    The list display includes the user, a preview of the related post, a preview of the comment text, and the creation date, with search functionality for the comment text and user username.
    """

    list_display = ("user", "post_preview", "text_preview", "created_at")
    search_fields = ("text", "user__username")

    def post_preview(self, obj):
        """Helper method to display a shortened preview of the related post in the admin list view for comments."""
        return str(obj.post)[:30] + "..."

    def text_preview(self, obj):
        """Helper method to display a shortened preview of the comment text in the admin list view for comments."""
        return obj.text[:50] + "..."


@admin.register(LostItem)
class LostItemAdmin(admin.ModelAdmin):
    """
    Custom admin interface for the LostItem model, allowing administrators to manage lost item reports with fields for category, item name, location, resolution status, and creation date.
    The list display includes the category, item name, location, resolution status, and creation date, with filters for category and resolution status, and search functionality for item name and description.
    """

    list_display = ("category", "item_name", "location", "is_resolved", "created_at")
    list_filter = ("category", "is_resolved")
    search_fields = ("item_name", "description")


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
        """
        Helper method to indicate whether the story has associated media (image or video).
        This method returns a boolean value that is displayed as a boolean icon in the admin list view.
        """
        return bool(obj.image or obj.video)

    has_media.boolean = True
    has_media.short_description = "Media?"

    def likes_count(self, obj):
        """
        Helper method to display the total number of likes for the story in the admin list view.
        This method retrieves the count of users who have liked the story from the liked_by ManyToMany relationship and returns it for display.
        """
        return obj.liked_by.count()

    likes_count.short_description = "Likes"

    def views_count(self, obj):
        """
        Helper method to display the total number of views for the story in the admin list view.
        This method retrieves the count of users who have viewed the story from the viewed_by ManyToMany relationship and returns it for display.
        """
        return obj.viewed_by.count()

    views_count.short_description = "Views"

    def is_expired(self, obj):
        """
        Helper method to indicate whether the story has expired based on its creation time.
        This method checks if the story is expired by calling the is_expired property of the Story model and returns a boolean value that is displayed as a boolean icon in the admin list view.
        """
        return obj.is_expired

    is_expired.boolean = True
    is_expired.short_description = "Expired?"
