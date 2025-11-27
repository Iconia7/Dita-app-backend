from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
# We removed 'mpesa_callback' and added the new classes here:
from api.views import RegisterView, UserViewSet, EventViewSet, PaymentViewSet, InitiatePaymentView, PayHeroCallbackView

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'events', EventViewSet)
router.register(r'payments', PaymentViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # The Router handles users, events, and payments lists
    path('api/', include(router.urls)),
    
    # The New Payment Endpoints (Using .as_view() because they are classes now)
    path('api/pay/', InitiatePaymentView.as_view(), name='pay'),
    path('api/mpesa/callback/', PayHeroCallbackView.as_view(), name='callback'),
    path('api/register/', RegisterView.as_view(), name='register'),
]