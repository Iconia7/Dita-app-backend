import os
from datetime import timedelta

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .models import Payment
from .serializers import PaymentSerializer
from .utils import initiate_payhero_push
from apps.users.models import User


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing payments, allowing authenticated users to view their payment history and details.
    This ViewSet provides read-only access to payment records associated with the authenticated user, ensuring that users can only see their own payment information.
    """

    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(student=self.request.user)


class InitiatePaymentView(APIView):
    """
    APIView for initiating a payment, allowing users to start the payment process by providing their phone number and user ID.
    This view handles the creation of a payment record and initiates the STK push request to the PayHero API.
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """Handle POST requests to initiate a payment, validating input and interacting with the PayHero API."""
        phone_number = request.data.get("phone")
        user_id = request.data.get("user_id")
        amount = 200

        if not phone_number or not user_id:
            return Response({"error": "Phone and User ID are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        external_reference = f"dita-pay-{student_user.id}-{int(timezone.now().timestamp())}"

        try:
            Payment.objects.create(
                student=student_user,
                phone_number=phone_number,
                amount=amount,
                external_reference=external_reference,
                status="pending",
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        payhero_response = initiate_payhero_push(phone_number, amount, external_reference)
        if not payhero_response:
            return Response({"error": "Failed to initiate STK push."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "STK push sent. Enter PIN."}, status=status.HTTP_200_OK)


class PayHeroCallbackView(APIView):
    """
    APIView for handling PayHero callbacks, processing payment results and updating user membership status accordingly.
    This view validates the callback token, processes the payment result, updates the payment record, and extends the user's membership if the payment was successful.
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """Handle POST requests from PayHero callbacks, validating the token and processing payment results."""
        secret_token = request.query_params.get("token")
        expected_token = os.getenv("PAYHERO_CALLBACK_SECRET")

        if secret_token != expected_token:
            print(f"SECURITY ALERT: Invalid Callback Token from {request.META.get('REMOTE_ADDR')}")
            return Response({"message": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        callback_data = request.data.get("response") or request.data
        external_reference = callback_data.get("ExternalReference") or callback_data.get("User_Reference")

        if not external_reference:
            return Response({"message": "No Reference Found"}, status=status.HTTP_200_OK)

        try:
            payment = Payment.objects.get(external_reference=external_reference)
        except Payment.DoesNotExist:
            print(f"Payment not found for ref: {external_reference}")
            return Response({"message": "Payment not found"}, status=status.HTTP_200_OK)

        # Process the payment result and update membership
        if callback_data.get("Success") or callback_data.get("Status") == "Success":
            payment.status = "completed"
            payment.mpesa_receipt = callback_data.get("MpesaReceiptNumber")
            payment.save()

            student = payment.student
            now = timezone.now()
            semester_length = timedelta(days=120)

            if student.membership_expiry and student.membership_expiry > now:
                student.membership_expiry += semester_length
            else:
                student.membership_expiry = now + semester_length

            student.save()
            print(f"SUCCESS: Membership extended for {student.username}")
        else:
            payment.status = "failed"
            payment.save()
            print(f"FAILED: Payment failed for ref {external_reference}")

        return Response({"ResultCode": 0, "ResultDesc": "Accepted"}, status=status.HTTP_200_OK)
