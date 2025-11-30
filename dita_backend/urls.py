from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static # <--- MAKE SURE THIS IS IMPORTED
from api import views
from rest_framework.routers import DefaultRouter
from api.views import (
    UserViewSet, EventViewSet, PaymentViewSet, 
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

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 
# ^^^ FIXED: changed 'stat' to 'static'