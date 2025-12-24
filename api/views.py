from datetime import timedelta
import random
import requests
import threading
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.core.files.storage import FileSystemStorage
from django.db.models import Q  # <--- Add this at the top

# DRF Imports
from api.permissions import IsOwnerOrReadOnly
from dita_backend.utils import process_exam_excel
from rest_framework import viewsets, status, generics
from rest_framework.decorators import authentication_classes
from rest_framework.views import APIView
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly

# Local Imports
from .models import RSVP, AppConfig, AppUpdate, CommunityComment, CommunityPost, Exam, LostItem, PasswordResetOTP, Promotion, Task, User, Event, Payment, Resource, Announcement
from .serializers import (
    AppConfigSerializer, CommunityCommentSerializer, CommunityPostSerializer, ExamSerializer, LostItemSerializer, MyTokenObtainPairSerializer, PromotionSerializer, TaskSerializer, UserSerializer, EventSerializer, PaymentSerializer, 
    RegisterSerializer, ResourceSerializer, AnnouncementSerializer
)
from .payhero_utils import initiate_payhero_push
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.authentication import JWTAuthentication


# ==========================================
#  STANDARD VIEWSETS (CRUD)
# ==========================================

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

class EmailThread(threading.Thread):
    def __init__(self, subject, message, from_email, recipient_list):
        self.subject = subject
        self.message = message
        self.from_email = from_email
        self.recipient_list = recipient_list
        threading.Thread.__init__(self)

    def run(self):
        try:
            print("⏳ Attempting to send email in background...")
            send_mail(
                self.subject,
                self.message,
                self.from_email,
                self.recipient_list,
                fail_silently=False,
            )
            print("✅ Email sent successfully!")
        except Exception as e:
            print(f"❌ Error sending email: {e}")

# --- 2. Updated View ---

@api_view(['GET'])
@permission_classes([AllowAny]) # Allow everyone to see the leaderboard
def get_leaderboard(request):
    # Fetch top 20 students with > 0 points
    top_students = User.objects.filter(points__gt=0).order_by('-points')[:20]
    
    # We build a custom list because we don't want to expose sensitive info like phone/email
    data = []
    for user in top_students:
        avatar_url = user.avatar.url if user.avatar else None
        # Ensure full URL for images if needed
        if avatar_url and not avatar_url.startswith('http'):
            avatar_url = request.build_absolute_uri(avatar_url)
            
        data.append({
            'username': user.username,
            'program': user.program,
            'points': user.points,
            'avatar': avatar_url
        })
        
    return Response(data)


@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    
    email = request.data.get('email')
    if not email:
        return Response({'error': 'Email is required'}, status=400)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # Pretend it worked for security
        return Response({'error': 'Email not found. Please register first.'}, status=404)

    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))

    # Save OTP
    PasswordResetOTP.objects.filter(user=user).delete()
    PasswordResetOTP.objects.create(user=user, otp=otp)

    # --- 3. Send Email in Background (Non-Blocking) ---
    subject = 'DITA App Password Reset'
    message = f'Your verification code is: {otp}. It expires in 10 minutes.'
    
    EmailThread(
        subject, 
        message, 
        settings.DEFAULT_FROM_EMAIL, 
        [email]
    ).start()

    # Return success immediately without waiting for Gmail
    return Response({'message': 'OTP sent successfully'})

@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password_phone(request):
    """
    Called by Flutter after Firebase successfully verifies the OTP.
    """
    phone = request.data.get('phone')
    new_password = request.data.get('new_password')

    if not phone or not new_password:
        return Response({'error': 'Phone and new password are required'}, status=400)

    # 1. Clean the phone input
    phone = phone.replace(" ", "").replace("-", "")

    # 2. Find the user (Handle +254 vs 07 formats)
    user = None
    
    # Check 1: Exact Match (e.g. +254712345678)
    # NOTE: Ensure your User model has 'phone_number'. If it is named 'phone', change below.
    user = User.objects.filter(phone_number=phone).first()

    if not user:
        # Check 2: If input is +254, try Local format (07...)
        if phone.startswith('+254'):
            local_format = '0' + phone[4:] 
            user = User.objects.filter(phone_number=local_format).first()
        
        # Check 3: If input is 07, try Intl format (+254...)
        elif phone.startswith('0'):
            intl_format = '+254' + phone[1:]
            user = User.objects.filter(phone_number=intl_format).first()

    if not user:
        return Response({'error': 'User not found with this phone number.'}, status=404)

    # 3. Set New Password
    user.set_password(new_password)
    user.save()

    return Response({'message': 'Password reset successful successfully!'})

# ==========================================
#  TEXTBEE CONFIGURATION
# ==========================================
TEXTBEE_API_KEY = "1dcae381-e559-4d67-9ebb-56c45eb23c61"
TEXTBEE_DEVICE_ID = "694bc64beaf21e40b5f51510"

def send_textbee_sms(phone_number, message):
    url = f"https://api.textbee.dev/api/v1/gateway/devices/{TEXTBEE_DEVICE_ID}/sendSMS"
    payload = {
        "recipients": [phone_number],
        "message": message
    }
    headers = {"x-api-key": TEXTBEE_API_KEY}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code == 200
    except Exception as e:
        print(f"TextBee Error: {e}")
        return False

# ==========================================
#  UPDATED AUTH VIEWS
# ==========================================

@api_view(['POST'])
@permission_classes([AllowAny])
def request_sms_otp(request):
    """
    1. Receive Phone.
    2. Check User.
    3. Generate OTP.
    4. Send via TextBee.
    """
    phone = request.data.get('phone')
    
    if not phone:
        return Response({'error': 'Phone number is required'}, status=400)

    # Clean Phone (Convert 07xx to +254xx)
    clean_phone = phone.strip()
    if clean_phone.startswith('0'):
        clean_phone = '+254' + clean_phone[1:]
    
    # Find User
    user = User.objects.filter(phone_number=clean_phone).first() # Ensure your model field is 'phone_number'
    
    # Fallback checks if user stored number differently
    if not user:
         user = User.objects.filter(phone_number=phone).first()

    if not user:
        return Response({'error': 'User not found with this phone number.'}, status=404)

    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))

    # Save OTP to DB (Reuse your existing PasswordResetOTP model)
    PasswordResetOTP.objects.filter(user=user).delete()
    PasswordResetOTP.objects.create(user=user, otp=otp)

    # Send SMS via TextBee
    message = f"[DITA APP] Your One Time Password (OTP) is: {otp}. Valid for 10 minutes."
    sent = send_textbee_sms(clean_phone, message)

    if sent:
        return Response({'message': 'OTP sent successfully via SMS'})
    else:
        return Response({'error': 'Failed to send SMS. Check Gateway status.'}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password_with_otp(request):
    """
    Now accepts 'identifier' (which can be email OR phone)
    """
    identifier = request.data.get('identifier') # Can be phone or email
    otp = request.data.get('otp')
    new_password = request.data.get('new_password')

    if not all([identifier, otp, new_password]):
        return Response({'error': 'All fields are required'}, status=400)

    # 1. Find User (Try Email first, then Phone)
    user = User.objects.filter(email=identifier).first()
    
    if not user:
        # Try Phone formatting
        clean_phone = identifier.strip()
        if clean_phone.startswith('0'):
            clean_phone = '+254' + clean_phone[1:]
        
        user = User.objects.filter(phone_number=clean_phone).first()
        if not user: 
            user = User.objects.filter(phone_number=identifier).first()

    if not user:
        return Response({'error': 'User not found'}, status=404)

    # 2. Verify OTP
    reset_entry = PasswordResetOTP.objects.filter(user=user, otp=otp).last()

    if not reset_entry or not reset_entry.is_valid():
        return Response({'error': 'Invalid or expired OTP'}, status=400)

    # 3. Reset Password
    user.set_password(new_password)
    user.save()

    # Cleanup
    reset_entry.delete()

    return Response({'message': 'Password reset successful!'})

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

class LostItemViewSet(viewsets.ModelViewSet):
    # Show newest first, and put 'Unresolved' items at the top
    queryset = LostItem.objects.all().order_by('is_resolved', '-created_at')
    serializer_class = LostItemSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        # Auto-attach the logged-in user
        serializer.save(user=self.request.user)
        
        
class CommunityPostViewSet(viewsets.ModelViewSet):
    queryset = CommunityPost.objects.all()
    serializer_class = CommunityPostSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    # Action to Like a post
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        post = self.get_object() 
        user = request.user
        
        if post.liked_by.filter(id=user.id).exists():
            post.liked_by.remove(user) # Unlike
            liked = False
        else:
            post.liked_by.add(user) # Like
            liked = True
            
        return Response({'status': 'toggled', 'likes': post.total_likes, 'is_liked': liked})

class CommunityCommentViewSet(viewsets.ModelViewSet):
    queryset = CommunityComment.objects.all()
    serializer_class = CommunityCommentSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    # Filter comments by post ID 
    def get_queryset(self):
        post_id = self.request.query_params.get('post_id')
        if post_id:
            return self.queryset.filter(post_id=post_id).order_by('created_at')
        return self.queryset        

def public_exam_search(request):
    exams = []
    query = request.GET.get('codes', '')
    
    if query:
        # Split by comma, strip spaces, uppercase
        codes_list = [c.strip().upper() for c in query.split(',')]
        
        # Build query
        db_query = Q()
        for code in codes_list:
            if code:
                db_query |= Q(course_code__istartswith=code)
        
        if db_query:
            exams = Exam.objects.filter(db_query).order_by('date')

    return render(request, 'exam_search.html', {'exams': exams})

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

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
@permission_classes([AllowAny])
@authentication_classes([])# <--- CHANGE THIS
def change_password(request):
    # 1. Get the user from the Token, NOT the body
    user_id = request.data.get('user_id')
    
    old_pass = request.data.get('old_password')
    new_pass = request.data.get('new_password')

    if not user_id or not old_pass or not new_pass:
        return Response({'error': 'Missing fields'}, status=400)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

    # 2. Verify Old Password (Security Check)
    if not user.check_password(old_pass):
        return Response({'error': 'Wrong old password'}, status=400)

    # 3. Set New Password
    user.set_password(new_pass)
    user.save()

    return Response({'message': 'Password updated successfully!'})

@api_view(['GET'])
@permission_classes([AllowAny])
def system_status(request):
    # Get the config object (or create default if it doesn't exist)
    config, created = AppConfig.objects.get_or_create(id=1)
    serializer = AppConfigSerializer(config)
    return Response(serializer.data)
  

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
    
class PromotionViewSet(viewsets.ReadOnlyModelViewSet):
    # Only show active promos, newest first
    queryset = Promotion.objects.filter(is_active=True).order_by('-created_at')
    serializer_class = PromotionSerializer
    permission_classes = [AllowAny]    


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