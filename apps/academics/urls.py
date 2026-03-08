from django.urls import path

from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"exams", views.ExamViewSet)
router.register(r"tasks", views.TaskViewSet, basename="tasks")
router.register(r"resources", views.ResourceViewSet)

urlpatterns = [
    path("upload-timetable/", views.upload_timetable),
    path("exam-search/", views.public_exam_search),
    *router.urls,
]
