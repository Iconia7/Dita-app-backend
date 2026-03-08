from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"stories", views.StoryViewSet)
router.register(r"story-comments", views.StoryCommentViewSet)
router.register(r"community-posts", views.CommunityPostViewSet)
router.register(r"community-comments", views.CommunityCommentViewSet)

urlpatterns = router.urls
