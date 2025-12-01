from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q  # <--- Add this at the top

# DRF Imports
from rest_framework import viewsets, status, generics
from rest_framework.views import APIView
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly

# Local Imports
from .models import RSVP, Exam, Task, User, Event, Payment, Resource, Announcement
from .serializers import (
    ExamSerializer, TaskSerializer, UserSerializer, EventSerializer, PaymentSerializer, 
    RegisterSerializer, ResourceSerializer, AnnouncementSerializer
)
from .payhero_utils import initiate_payhero_push


# ==========================================
#  STANDARD VIEWSETS (CRUD)
# ==========================================

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_queryset(self):
        queryset = User.objects.all()
        
        # Get the input from the app (it might be a username OR an admission number)
        search_term = self.request.query_params.get('username')
        
        if search_term is not None:
            # Filter: matches Username OR matches Admission Number (Case Insensitive)
            queryset = queryset.filter(
                Q(username__iexact=search_term) | 
                Q(admission_number__iexact=search_term)
            )
            
        return queryset

class ExamViewSet(viewsets.ReadOnlyModelViewSet): # ReadOnly because users don't edit exams
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer # Make sure to import this
    permission_classes = [AllowAny]

    def get_queryset(self):
        # Get the comma-separated list from URL
        # Example: /api/exams/?codes=ACS401,INS411
        codes_param = self.request.query_params.get('codes')
        
        if codes_param:
            # Split "ACS401,INS411" into ['ACS401', 'INS411']
            # Use .upper() to handle case sensitivity
            codes_list = [c.strip().upper() for c in codes_param.split(',')]
            return Exam.objects.filter(course_code__in=codes_list).order_by('date')
            
        return Exam.objects.none() # Return nothing if no codes provided
        
class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [AllowAny] 

    def get_queryset(self):
        # FIX 2: Filter based on the 'user_id' query param sent from Flutter
        # (e.g., /api/tasks/?user_id=6)
        user_id = self.request.query_params.get('user_id')
        
        if user_id:
            return Task.objects.filter(user_id=user_id).order_by('due_date')
        
        # If no ID provided, return nothing (security)
        return Task.objects.none()

    def perform_create(self, serializer):
        # FIX 3: Manually attach the user based on the ID sent in the body
        user_id = self.request.data.get('user_id')
        user = get_object_or_404(User, id=user_id)
        serializer.save(user=user)  


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all().order_by('date')
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    # --- Custom Actions inside ViewSet ---

    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def check_in(self, request, pk=None):
        """
        QR Code Scan Endpoint: /api/events/{id}/check_in/
        """
        event = self.get_object()
        
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'User ID required'}, status=400)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

        # Check if already scanned
        if event.checked_in_users.filter(id=user.id).exists():
            return Response({'message': 'Already checked in!'}, status=400)
        
        # Record attendance
        event.checked_in_users.add(user)
        
        # Award Points
        user.points += 20
        user.save()

        return Response({
            'message': 'Check-in Successful! +20 Points', 
            'new_points': user.points
        })
    
    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def rsvp(self, request, pk=None):
        """
        RSVP Toggle Endpoint: /api/events/{id}/rsvp/
        """
        event = self.get_object()
        user_id = request.data.get('user_id')
        
        try:
            user = User.objects.get(id=user_id)
            
            # Toggle RSVP (If exists delete, if not create)
            rsvp, created = RSVP.objects.get_or_create(user=user, event=event)
            
            if not created:
                # If it existed, delete it (Cancel RSVP)
                rsvp.delete()
                return Response({"status": "un-rsvped", "message": "RSVP cancelled"})
                
            return Response({"status": "rsvped", "message": "RSVP successful"})
            
        except Exception as e:
            return Response({"error": str(e)}, status=400)


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


# ==========================================
#  CUSTOM API VIEWS
# ==========================================

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


class InitiatePaymentView(APIView):
    permission_classes = [AllowAny] 

    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone')
        user_id = request.data.get('user_id')
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