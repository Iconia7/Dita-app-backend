from django.urls import path

from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"history", views.PaymentViewSet, basename="payment-history")

urlpatterns = [
    path("mpesa/initiate/", views.InitiatePaymentView.as_view(), name="mpesa-initiate"),
    path("mpesa/callback/", views.MpesaCallbackView.as_view(), name="mpesa-callback"),
    *router.urls,
]
