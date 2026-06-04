from django.urls import path

from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

router = DefaultRouter()
router.register(r"users", views.UserViewSet, basename="user")
router.register(r"achievements", views.AchievementViewSet)
router.register(r"user-achievements", views.UserAchievementViewSet, basename="user-achievements")

urlpatterns = [
    path("auth/login/", views.MyTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("auth/change-password/", views.change_password, name="change_password"),
    path("auth/reset-password-phone/", views.reset_password_phone, name="reset-password-phone"),
    path("auth/request-otp/", views.request_otp, name="request_otp"),
    path("auth/reset-password-otp/", views.reset_password_otp, name="reset_password_otp"),
    path("leaderboard/", views.get_leaderboard, name="leaderboard"),
    path("verify-voter/", views.verify_voter, name="verify_voter"),
    *router.urls,
]
