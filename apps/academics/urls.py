from django.urls import path

from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"exams", views.ExamViewSet)
router.register(r"tasks", views.TaskViewSet, basename="tasks")
router.register(r"resources", views.ResourceViewSet)

urlpatterns = [
    path("updates/latest/", views.check_update, name="check_update"),
    path("status/", views.system_status, name="system_status"),
    path("portal-sync/", views.portal_sync_exams, name="portal_sync_exams"),
    path("upload-timetable/", views.upload_timetable, name="upload_timetable"),
    path("exam-search/", views.public_exam_search, name="public_exam_search"),
    *router.urls,
]
