from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"payments", views.PaymentViewSet, basename="payments")

urlpatterns = [
    path("mpesa/initiate/", views.InitiatePaymentView.as_view()),
    path("mpesa/callback/", views.PayHeroCallbackView.as_view()),
    *router.urls,
]
