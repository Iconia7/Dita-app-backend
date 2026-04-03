from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

# Individual View Imports for Legacy Endpoints
from apps.academics.views import (
    upload_timetable, 
    public_exam_search, 
    check_update, 
    system_status, 
    portal_sync_exams
)
from apps.users.views import (
    RegisterView,
    change_password,
    reset_password_phone,
    get_leaderboard,
    verify_voter,
    MyTokenObtainPairView
)
from apps.payments.views import InitiatePaymentView, MpesaCallbackView
from apps.study_groups.views import group_landing_page

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # --- Consolidated API (v1) ---
    # Includes all modular app routers and views at the /api/ root
    path("api/", include("apps.users.urls")),
    path("api/", include("apps.events.urls")),
    path("api/", include("apps.payments.urls")),
    path("api/", include("apps.community.urls")),
    path("api/", include("apps.academics.urls")),
    path("api/", include("apps.study_groups.urls")),

    # --- Legacy / Flutter App Compatibility Routes ---
    # These ensure existing mobile app versions and templates continue to work
    path("api/register/", RegisterView.as_view(), name="register_legacy"),
    path("api/pay/", InitiatePaymentView.as_view(), name="pay_legacy"),
    path("api/mpesa/callback/", MpesaCallbackView.as_view(), name="callback_legacy"),
    path("api/change-password/", change_password, name="change_password_legacy"),
    path("api/auth/reset-password-phone/", reset_password_phone, name="reset-password-phone_legacy"),
    path("api/leaderboard/", get_leaderboard, name="leaderboard_legacy"),
    path("api/verify-voter/", verify_voter, name="verify_voter_legacy"),
    path("api/check-update/", check_update, name="check_update_legacy"),
    path("api/system-status/", system_status, name="system_status_legacy"),
    path("api/portal-sync/", portal_sync_exams, name="portal_sync_legacy"),
    path("api/login/", MyTokenObtainPairView.as_view(), name="token_obtain_pair_legacy"),
    
    # --- Specialized Web & HTML Routes ---
    path("upload-timetable/", upload_timetable, name="upload_timetable"),
    path("public/exams/", public_exam_search, name="public_exam_search"),
    path("group/<int:group_id>/", group_landing_page, name="group_landing_legacy"),

    # --- API Documentation ---
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
