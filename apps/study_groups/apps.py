from django.apps import AppConfig


class StudyGroupsConfig(AppConfig):
    """
    Configuration for the Study Groups app, which includes models for study groups, group messages, and group memberships.
    This configuration sets up the default auto field type, app name, and label for the app.
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.study_groups"
    label = "study_groups"
