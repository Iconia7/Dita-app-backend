from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"study-groups", views.StudyGroupViewSet)

urlpatterns = [
    path("groups/<int:group_id>/", views.group_landing_page),
    *router.urls,
]
