from datetime import timedelta
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.core.files.storage import FileSystemStorage
from django.db.models import Q  # <--- Add this at the top

# DRF Imports
from dita_backend.utils import process_exam_excel
from rest_framework import viewsets, status, generics
from rest_framework.views import APIView
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly

# Local Imports
from .models import RSVP, AppUpdate, Exam, Task, User, Event, Payment, Resource, Announcement
from .serializers import (
    ExamSerializer, TaskSerializer, UserSerializer, EventSerializer, PaymentSerializer, 
    RegisterSerializer, ResourceSerializer, AnnouncementSerializer
)
from .payhero_utils import initiate_payhero_push


# ==========================================
#  STANDARD VIEWSETS (CRUD)
# ==========================================

def upload_timetable(request):
    context = {}
    if request.method == 'POST' and request.FILES.get('myfile'):
        myfile = request.FILES['myfile']
        fs = FileSystemStorage()
        filename = fs.save(myfile.name, myfile)
        file_path = fs.path(filename)
        
        try:
            # 1. Process Excel
            exams_data = process_exam_excel(file_path)
            
            # 2. DELETE OLD DATA (Safe way to update timetable)
            Exam.objects.all().delete()
            
            # 3. Insert New Data
            exam_objects = [
                Exam(
                    course_code=item['course_code'],
                    title=item['title'],
                    date=item['date'],          # datetime object
                    end_time=item['end_time'],
                    venue=item['venue'],
                    duration_hours=item['duration_hours']
                ) for item in exams_data
            ]
            
            Exam.objects.bulk_create(exam_objects)
            context['success'] = f"Success! Imported {len(exam_objects)} exams."
            
        except Exception as e:
            context['error'] = f"Error: {str(e)}"
        
        fs.delete(filename)
        
    return render(request, 'upload.html', context)

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
    
@api_view(['GET'])
@permission_classes([AllowAny])
def check_update(request):
    latest_update = AppUpdate.objects.first()
    if latest_update:
        # 1. Get the relative URL (e.g., /media/updates/v1.apk)
        relative_url = latest_update.apk_file.url

        # 2. Convert it to a full absolute URL if it isn't one already
        if not relative_url.startswith('http'):
            download_url = request.build_absolute_uri(relative_url)
        else:
            download_url = relative_url

        return Response({
            'version_code': latest_update.version_code,
            'download_url': download_url,  # <--- Send the Full URL
            'release_notes': latest_update.release_notes,
            'is_mandatory': latest_update.is_mandatory
        })
    return Response({}, status=404) 

@api_view(['POST'])
@permission_classes([IsAuthenticated]) # <--- CHANGE THIS
def change_password(request):
    # 1. Get the user from the Token, NOT the body
    user = request.user 
    
    old_pass = request.data.get('old_password')
    new_pass = request.data.get('new_password')

    if not old_pass or not new_pass:
        return Response({'error': 'Missing fields'}, status=400)

    # 2. Verify Old Password
    if not user.check_password(old_pass):
        return Response({'error': 'Wrong old password'}, status=400)

    # 3. Set New Password
    user.set_password(new_pass)
    user.save()

    return Response({'message': 'Password updated successfully!'})
  

class ExamViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        # If no params, return all (or none, depending on your preference)
        # Your previous code returned none if no params, which is good for performance
        codes_param = self.request.query_params.get('codes')
        
        if codes_param:
            # 1. Clean the inputs (e.g., "ACS 401" -> "ACS401")
            codes_list = [c.strip().upper().replace(" ", "") for c in codes_param.split(',')]
            
            # 2. Build the "Smart" Query
            query = Q()
            for code in codes_list:
                if code: 
                    # Matches "ACS401", "ACS401A", "ACS401T"
                    query |= Q(course_code__istartswith=code)
            
            # Order by date so the app shows them chronologically
            return Exam.objects.filter(query).order_by('date')
            
        return Exam.objects.none()
        
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
    def get_queryset(self):
        # 1. Check for filter
        attended_by = self.request.query_params.get('attended_by')
        
        if attended_by:
            # HISTORY MODE: Filter by user, show NEWEST first (Descending)
            return Event.objects.filter(checked_in_users__id=attended_by).order_by('-date')
        
        # UPCOMING MODE: Show ALL, show SOONEST first (Ascending)
        # You might also want to hide past events: .filter(date__gte=timezone.now())
        return Event.objects.all().order_by('date')    


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