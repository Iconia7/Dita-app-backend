from django.urls import path

from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

router = DefaultRouter()
router.register(r"users", views.UserViewSet)
router.register(r"achievements", views.AchievementViewSet)
router.register(r"user-achievements", views.UserAchievementViewSet, basename="user-achievements")

urlpatterns = [
    path("auth/login/", views.MyTokenObtainPairView.as_view()),
    path("auth/refresh/", TokenRefreshView.as_view()),
    path("auth/register/", views.RegisterView.as_view()),
    path("auth/change-password/", views.change_password),
    path("auth/reset-password-phone/", views.reset_password_phone),
    path("leaderboard/", views.get_leaderboard),
    *router.urls,
]
