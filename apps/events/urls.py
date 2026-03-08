from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"events", views.EventViewSet)
router.register(r"announcements", views.AnnouncementViewSet)

urlpatterns = router.urls
