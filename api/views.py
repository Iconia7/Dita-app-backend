from django.shortcuts import render
from django.utils import timezone
from rest_framework import viewsets, status, generics
from rest_framework.views import APIView
# 1. IMPORT 'action' (lowercase)
from rest_framework.decorators import api_view, permission_classes, action 
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from .models import User, Event, Payment, Resource, Announcement
from .serializers import (
    UserSerializer, EventSerializer, PaymentSerializer, 
    RegisterSerializer, ResourceSerializer, AnnouncementSerializer
)
from .payhero_utils import initiate_payhero_push

# --- STANDARD VIEWSETS ---

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_queryset(self):
        queryset = User.objects.all()
        username = self.request.query_params.get('username')
        if username is not None:
            queryset = queryset.filter(username=username)
        return queryset

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all().order_by('date')
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    # 2. USE '@action' (lowercase)
    @action(detail=True, methods=['post'], permission_classes=[AllowAny]) # <--- AllowAny
    def rsvp(self, request, pk=None):
        event = self.get_object()
        
        # Get User ID from the App payload
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'User ID required'}, status=400)
            
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
        
        # Toggle Logic
        if event.attendees.filter(id=user.id).exists():
            event.attendees.remove(user)
            return Response({'status': 'RSVP Cancelled', 'joined': False})
        else:
            event.attendees.add(user)
            return Response({'status': 'RSVP Successful', 'joined': True})

    # 2. Attendance/Scan Logic (UPDATED)
    @action(detail=True, methods=['post'], permission_classes=[AllowAny]) # <--- AllowAny
    def check_in(self, request, pk=None):
        event = self.get_object()
        
        # Get User ID from App
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'User ID required'}, status=400)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

        if event.checked_in_users.filter(id=user.id).exists():
            return Response({'message': 'Already checked in!'}, status=400)
        
        event.checked_in_users.add(user)
        
        # Award Points
        user.points += 20
        user.save()

        return Response({
            'message': 'Check-in Successful! +20 Points', 
            'new_points': user.points
        })

class ResourceViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.filter(is_active=True).order_by('-date_posted')
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

# --- CUSTOM VIEWS ---

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

class InitiatePaymentView(APIView):
    permission_classes = [AllowAny] 

    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone')
        user_id = request.data.get('user_id')
        amount = 500 

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
                status='pending'
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        payhero_response = initiate_payhero_push(phone_number, amount, external_reference)

        if not payhero_response:
             return Response({"error": "Failed to initiate STK push."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "STK push sent. Enter PIN."}, status=status.HTTP_200_OK)


class PayHeroCallbackView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        print(f"DEBUG: PayHero Callback: {request.data}")

        callback_data = request.data.get('response') or request.data
        external_reference = callback_data.get('ExternalReference') or callback_data.get('User_Reference')
        
        if not external_reference:
            return Response({"message": "No Reference Found"}, status=status.HTTP_200_OK)

        try:
            payment = Payment.objects.get(external_reference=external_reference)
        except Payment.DoesNotExist:
            print(f"Payment not found for ref: {external_reference}")
            return Response({"message": "Payment not found"}, status=status.HTTP_200_OK)

        if callback_data.get('Success') == True or callback_data.get('Status') == 'Success':
            payment.status = 'completed'
            payment.mpesa_receipt = callback_data.get('MpesaReceiptNumber')
            payment.save()

            student = payment.student
            
            # SEMESTER LOGIC (120 Days)
            from datetime import timedelta
            now = timezone.now()
            semester_length = timedelta(days=120)

            if student.membership_expiry and student.membership_expiry > now:
                student.membership_expiry += semester_length
            else:
                student.membership_expiry = now + semester_length
            
            student.save()
            print(f"SUCCESS: Membership extended for {student.username}")
        else:
            payment.status = 'failed'
            payment.save()
            print(f"FAILED: Payment failed for ref {external_reference}")

        return Response({"ResultCode": 0, "ResultDesc": "Accepted"}, status=status.HTTP_200_OK)