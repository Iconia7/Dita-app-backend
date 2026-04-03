from django.conf import settings
from django.db import models


class StudyGroup(models.Model):
    """Model representing a study group for a specific course, including fields for name, course code, description, creator, members, and creation timestamp."""

    name = models.CharField(max_length=100)
    course_code = models.CharField(max_length=50)
    description = models.TextField()
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_groups")
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="study_groups")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.course_code}: {self.name}"


class GroupMessage(models.Model):
    """Model representing a message posted within a study group, including fields for the associated group, user, content, and timestamp."""

    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name="messages")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.user.username} in {self.group.name}: {self.content[:30]}"
