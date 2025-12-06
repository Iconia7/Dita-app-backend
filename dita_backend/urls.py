from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static # <--- MAKE SURE THIS IS IMPORTED
from api import views
from rest_framework.routers import DefaultRouter
from api.views import (
    MyTokenObtainPairView, UserViewSet, EventViewSet, PaymentViewSet, 
    InitiatePaymentView, PayHeroCallbackView, 
    RegisterView, AnnouncementViewSet, ResourceViewSet
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'events', EventViewSet)
router.register(r'payments', PaymentViewSet)
router.register(r'announcements', AnnouncementViewSet)
router.register(r'resources', ResourceViewSet)
router.register(r'tasks', views.TaskViewSet, basename='task')
router.register(r'exams', views.ExamViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API Routes
    path('api/', include(router.urls)),
    
    # Custom Endpoints
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/pay/', InitiatePaymentView.as_view(), name='pay'),
    path('api/mpesa/callback/', PayHeroCallbackView.as_view(), name='callback'),
    path('api/updates/latest/', views.check_update, name='check_update'),
    path('api/change-password/', views.change_password, name='change_password'),
    path('upload-timetable/', views.upload_timetable, name='upload_timetable'),
    path('api/login/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/request-reset/', views.request_password_reset, name='request-reset'),
    path('api/auth/confirm-reset/', views.reset_password_with_otp, name='confirm-reset'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 
# ^^^ FIXED: changed 'stat' to 'static'