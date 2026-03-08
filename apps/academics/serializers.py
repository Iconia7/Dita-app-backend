from rest_framework import serializers
from .models import Exam, Resource, Task


class ExamSerializer(serializers.ModelSerializer):
    """Serializer for the Exam model, including all fields."""

    class Meta:
        model = Exam
        fields = "__all__"


class TaskSerializer(serializers.ModelSerializer):
    """
    Serializer for the Task model, including all fields.
    The user and created_at fields are set to read-only to prevent modification through the API,
    ensuring that the task is always associated with the correct user and timestamp when created.
    """

    class Meta:
        model = Task
        fields = "__all__"
        read_only_fields = ["user", "created_at"]


class ResourceSerializer(serializers.ModelSerializer):
    """Serializer for the Resource model, including all fields."""

    class Meta:
        model = Resource
        fields = ["id", "title", "resource_type", "link", "file", "description"]
