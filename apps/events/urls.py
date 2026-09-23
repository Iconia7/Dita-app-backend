from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"events", views.EventViewSet)
router.register(r"announcements", views.AnnouncementViewSet)

urlpatterns = [
    path("hack-fest-26/register/", views.HackFestRegistrationView.as_view(), name="hackfest-register"),
    path("hack-fest-26/capacity/", views.HackFestRegistrationView.as_view(), name="hackfest-capacity"),
    path("events/hack-fest-26/register/", views.HackFestRegistrationView.as_view(), name="events-hackfest-register"),
    path("events/hack-fest-26/capacity/", views.HackFestRegistrationView.as_view(), name="events-hackfest-capacity"),
] + router.urls
