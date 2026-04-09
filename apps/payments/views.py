import logging
import os
from datetime import timedelta

import hmac
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import User

from .models import Payment
from .serializers import PaymentSerializer
from .utils import initiate_stk_push

logger = logging.getLogger(__name__)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing payments, allowing authenticated users to view their payment history and details.
    """

    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(student=self.request.user)


class InitiatePaymentView(APIView):
    """
    APIView for initiating an M-Pesa STK push.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        phone_number = request.data.get("phone")
        user_id = request.user.id  # Force the user ID to be the authenticated user
        amount = 200

        if phone_number and phone_number.startswith("0"):
            phone_number = "254" + phone_number[1:]
        elif phone_number and phone_number.startswith("+"):
            phone_number = phone_number[1:]

        if not phone_number or not user_id:
            return Response({"error": "Phone and User ID are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        external_reference = f"dita-pay-{student_user.id}-{int(timezone.now().timestamp())}"

        try:
            payment = Payment.objects.create(
                student=student_user,
                phone_number=phone_number,
                amount=amount,
                external_reference=external_reference,
                status="pending",
            )
        except Exception as e:
            logger.error(f"Error creating payment record: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        response = initiate_stk_push(phone_number, amount, external_reference)
        if not response:
            return Response({"error": "Failed to initiate M-Pesa STK push."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Store Safaricom IDs for reliable callback matching
        payment.checkout_request_id = response.get("CheckoutRequestID")
        payment.merchant_request_id = response.get("MerchantRequestID")
        payment.save()

        return Response({"message": "STK push sent. Enter PIN."}, status=status.HTTP_200_OK)


class MpesaCallbackView(APIView):
    """
    APIView for handling Safaricom M-Pesa callbacks.
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        # Validate Secret Token
        token = request.query_params.get("token")
        expected_token = os.getenv("MPESA_CALLBACK_SECRET")
        
        if not expected_token or not token or not hmac.compare_digest(token, expected_token):
            logger.error(f"UNAUTHORIZED: Callback attempt with invalid token: {token}")
            return Response({"ResultCode": 1, "ResultDesc": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

        data = request.data.get("Body", {}).get("stkCallback", {})
        code = data.get("ResultCode")
        meta = data.get("CallbackMetadata", {}).get("Item", [])
        receipt, phone = None, None

        for item in meta:
            if item.get("Name") == "MpesaReceiptNumber":
                receipt = item.get("Value")
            if item.get("Name") == "PhoneNumber":
                phone = item.get("Value")

        checkout_request_id = data.get("CheckoutRequestID")

        if code == 0:
            # Reliable lookup using CheckoutRequestID
            payment = None
            if checkout_request_id:
                payment = Payment.objects.filter(checkout_request_id=checkout_request_id, status="pending").last()
            
            # Fallback to phone number if CheckoutRequestID lookup fails (for compatibility or edge cases)
            if not payment and phone:
                payment = Payment.objects.filter(phone_number__contains=str(phone), status="pending").last()

            if payment:
                payment.status = "completed"
                payment.mpesa_receipt = receipt
                payment.save()

                student = payment.student
                now = timezone.now()
                # Extend membership by 120 days
                student.membership_expiry = (student.membership_expiry or now) + timedelta(days=120)
                student.save()
                logger.info(f"SUCCESS: Membership extended for {student.username}")
            else:
                logger.warning(f"Payment record not found for phone: {phone}")
        else:
            logger.warning(f"FAILED: M-Pesa payment failed with code {code}")

        return Response({"ResultCode": 0, "ResultDesc": "Accepted"}, status=status.HTTP_200_OK)
