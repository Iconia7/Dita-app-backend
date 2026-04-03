from django.conf import settings
from django.conf.urls.static import static  # <--- MAKE SURE THIS IS IMPORTED
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api import views
from api.views import (
    AnnouncementViewSet,
    EventViewSet,
    InitiatePaymentView,
    MyTokenObtainPairView,
    MpesaCallbackView,
    PaymentViewSet,
    RegisterView,
    ResourceViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register(r"users", UserViewSet)
router.register(r"events", EventViewSet)
router.register(r"payments", PaymentViewSet, basename="payment")
router.register(r"announcements", AnnouncementViewSet)
router.register(r"resources", ResourceViewSet)
router.register(r"tasks", views.TaskViewSet, basename="task")
router.register(r"exams", views.ExamViewSet)
router.register(r"community-posts", views.CommunityPostViewSet)
router.register(r"community-comments", views.CommunityCommentViewSet)
router.register(r"promotions", views.PromotionViewSet)
router.register(r"stories", views.StoryViewSet)
router.register(r"story-comments", views.StoryCommentViewSet)
router.register(r"achievements", views.AchievementViewSet)
router.register(r"user-achievements", views.UserAchievementViewSet, basename="user-achievement")
router.register(r"study-groups", views.StudyGroupViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    # API Routes
    path("api/", include(router.urls)),
    # Custom Endpoints
    path("api/register/", RegisterView.as_view(), name="register"),
    path("api/pay/", InitiatePaymentView.as_view(), name="pay"),
    path("api/mpesa/callback/", MpesaCallbackView.as_view(), name="callback"),
    path("api/updates/latest/", views.check_update, name="check_update"),
    path("api/change-password/", views.change_password, name="change_password"),
    path("upload-timetable/", views.upload_timetable, name="upload_timetable"),
    path("api/login/", MyTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/status/", views.system_status, name="system-status"),
    path("public/exams/", views.public_exam_search, name="public_exam_search"),
    path("api/leaderboard/", views.get_leaderboard, name="leaderboard"),
    path("api/auth/reset-password-phone/", views.reset_password_phone, name="reset-password-phone"),
    path("group/<int:group_id>/", views.group_landing_page, name="group-landing"),
    path("api/verify-voter/", views.verify_voter, name="verify_voter"),
    path("api/portal-sync/", views.portal_sync_exams, name="portal_sync_exams"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# ^^^ FIXED: changed 'stat' to 'static'
