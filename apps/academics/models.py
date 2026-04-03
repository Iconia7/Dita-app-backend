from django.conf import settings
from django.db import models


class Exam(models.Model):
    """Model representing an exam schedule for a course, including fields for course code, title, date, end time, venue, and duration in hours."""

    course_code = models.CharField(max_length=50)
    title = models.CharField(max_length=200, blank=True, null=True)
    date = models.DateTimeField()
    end_time = models.TimeField(null=True, blank=True)
    venue = models.CharField(max_length=100)
    duration_hours = models.DecimalField(max_digits=4, decimal_places=2, default=2.0)

    def __str__(self):
        return f"{self.course_code} - {self.date.strftime('%d %b %H:%M')}"


class Task(models.Model):
    """Model representing a task for a user, including fields for title, description, due date, and completion status."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    due_date = models.DateTimeField()
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.user.username}"


class Resource(models.Model):
    """
    Model representing a resource for students, including fields for title, resource type, link, file upload, and description.
    The resource type is defined by a set of choices to categorize the type of resource being provided.
    """

    TYPE_CHOICES = [
        ("PDF", "PDF Document"),
        ("PPT", "Presentation (PPT/Slides)"),
        ("DOC", "Word Document"),
        ("XLS", "Excel Spreadsheet"),
        ("IMG", "Image"),
        ("ZIP", "Zip Archive"),
        ("LINK", "External Link"),
    ]
    title = models.CharField(max_length=200)
    resource_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    link = models.URLField(help_text="Link to Google Drive or Website", blank=True, null=True)
    file = models.FileField(upload_to="resources/", blank=True, null=True)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.title
