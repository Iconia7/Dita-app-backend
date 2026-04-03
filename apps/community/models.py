from django.conf import settings
from django.db import models

from cloudinary.models import CloudinaryField


class Story(models.Model):
    """Model representing a user's story, which can include images, videos, captions, and interactions such as views and likes."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stories")
    image = models.ImageField(upload_to="stories/", null=True, blank=True)
    video = CloudinaryField("video", resource_type="video", null=True, blank=True)
    caption = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    viewed_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="viewed_stories", blank=True)
    liked_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="liked_stories", blank=True)

    @property
    def is_expired(self):
        """Determine if the story has expired (older than 24 hours) and should no longer be visible."""
        from django.utils import timezone

        return self.created_at < timezone.now() - timezone.timedelta(hours=24)

    @property
    def total_likes(self):
        """Calculate the total number of likes for the story by counting the related users in the liked_by ManyToMany field."""
        return self.liked_by.count()

    class Meta:
        verbose_name_plural = "Stories"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username}'s Story - {self.id}"


class StoryComment(models.Model):
    """Model representing a comment made by a user on a story, including the related story, user, comment text, and timestamp."""

    story = models.ForeignKey(Story, related_name="comments", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.user.username} on Story {self.story.id}"


class CommunityPost(models.Model):
    """
    Model representing a post in the community section, allowing users to share content, categorize it, and interact through likes and comments.
    This model includes fields for the post content, category, anonymity option, and relationships to users who liked the post and users who commented on it.
    """

    CATEGORY_CHOICES = [
        ("ACADEMIC", "Academic Help 📚"),
        ("GENERAL", "General Chat 📢"),
        ("MARKET", "Marketplace 💼"),
        ("EVENTS", "Events & Fun 🎉"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="GENERAL")
    is_anonymous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to="community_uploads/", null=True, blank=True)
    liked_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="liked_posts", blank=True)

    @property
    def total_likes(self):
        """Calculate the total number of likes for the post by counting the related users in the liked_by ManyToMany field."""
        return self.liked_by.count()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username}: {self.content[:30]}..."


class CommunityComment(models.Model):
    """Model representing a comment made by a user on a community post, including the related post, user, comment text, and timestamp."""

    post = models.ForeignKey(CommunityPost, related_name="comments", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username}"


class LostItem(models.Model):
    """
    Model representing a lost or found item reported by a user, including details such as item name, description, category (lost or found), location, contact information, and resolution status.
    This model allows users to report lost or found items, providing a way for the community to assist in reuniting lost items with their owners or finding the rightful owner of found items.
    """

    TYPE_CHOICES = [("LOST", "Lost 🛑"), ("FOUND", "Found ✅")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    item_name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=10, choices=TYPE_CHOICES, default="LOST")
    location = models.CharField(max_length=100)
    image = models.ImageField(upload_to="lost_found/", null=True, blank=True)
    contact_phone = models.CharField(max_length=15)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category}: {self.item_name}"


class Promotion(models.Model):
    """Model representing a promotion, allowing the club to highlight specific services, events, or partners to users."""

    title = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to="promotions/", blank=True, null=True)
    link = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
