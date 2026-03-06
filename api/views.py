import os
from datetime import timedelta

# --- 1. NEW IMPORTS FOR SECURITY ---
import firebase_admin
from firebase_admin import auth, credentials

from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.core.files.storage import FileSystemStorage
from django.db.models import Q 

# DRF Imports
from api.permissions import IsOwnerOrReadOnly
from config.utils import process_exam_excel
from rest_framework import viewsets, status, generics, permissions, filters
from rest_framework.views import APIView
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly

# Local Imports
from .models import (
    Achievement, Announcement, AppConfig, AppUpdate, CommunityComment, CommunityPost, 
    Event, Exam, GroupMessage, LostItem, Payment, Promotion, Resource, Story, StoryComment, 
    StudyGroup, Task, User, UserAchievement, RSVP
)
from .serializers import (
    AchievementSerializer, AnnouncementSerializer, AppConfigSerializer, AppUpdateSerializer,
    CommunityCommentSerializer, CommunityPostSerializer, EventSerializer, 
    ExamSerializer, GroupMessageSerializer, MyTokenObtainPairSerializer, 
    PaymentSerializer, RegisterSerializer, ResourceSerializer, StorySerializer, StoryCommentSerializer,
    StoryViewerSerializer, StudyGroupSerializer, TaskSerializer, UserAchievementSerializer, UserSerializer,
    PromotionSerializer
)
from .payhero_utils import initiate_payhero_push
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.authentication import JWTAuthentication

# ==========================================
# 🔥 FIREBASE INITIALIZATION
# ==========================================
try:
    if not firebase_admin._apps:
        # 1. Determine the path based on Env Vars or defaults
        cred_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT_PATH')
        
        if not cred_path:
            if os.environ.get('RENDER'):
                cred_path = '/etc/secrets/serviceAccountKey.json'
            else:
                # Local development path
                cred_path = os.path.join(settings.BASE_DIR, 'config', 'serviceAccountKey.json')
                
                # Fallback: Check root folder
                if not os.path.exists(cred_path):
                     cred_path = os.path.join(settings.BASE_DIR, 'serviceAccountKey.json')

        # 2. Initialize the App
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print(f"✅ Firebase Admin SDK Initialized from: {cred_path}")
        else:
            print(f"⚠️ WARNING: Service Account Key not found at: {cred_path}")
            print("   Secure Phone Login will fail until the file is added.")

except Exception as e:
    # Use a warning instead of error so it doesn't look like a crash in the logs
    print(f"⚠️ Firebase Init Warning: {e}")


# ==========================================
#  STANDARD VIEWSETS (CRUD)
# ==========================================

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

# --- Updated View ---

@api_view(['GET'])
@permission_classes([AllowAny]) 
def get_leaderboard(request):
    top_students = User.objects.filter(points__gt=0).order_by('-points')[:20]
    data = []
    for user in top_students:
        avatar_url = user.avatar.url if user.avatar else None
        if avatar_url and not avatar_url.startswith('http'):
            avatar_url = request.build_absolute_uri(avatar_url)
            
        data.append({
            'username': user.username,
            'program': user.program,
            'points': user.points,
            'avatar': avatar_url
        })
        
    return Response(data)

# ==========================================
# 🔒 SECURE PHONE RESET (ENFORCED)
# ==========================================
@api_view(['POST'])
@permission_classes([AllowAny]) # Keeps endpoint open, but we check token inside
@authentication_classes([])
def reset_password_phone(request):
    """
    Called by Flutter after Firebase successfully verifies the OTP.
    SECURED: Verifies the Firebase ID Token.
    """
    new_password = request.data.get('new_password')
    
    # 1. GET TOKEN FROM HEADER
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        # ⚠️ If you haven't set up Firebase on backend yet, you can comment this block out temporarily
        return Response({'error': 'Missing or Invalid Firebase Token'}, status=401)

    id_token = auth_header.split(" ")[1]
    verified_phone = None

    # 2. VERIFY TOKEN WITH GOOGLE
    try:
        decoded_token = auth.verify_id_token(id_token)
        verified_phone = decoded_token.get('phone_number') # e.g., +2547...
    except Exception as e:
        print(f"Token Verification Failed: {e}")
        return Response({'error': 'Invalid or Expired Security Token'}, status=401)

    if not verified_phone:
        return Response({'error': 'Could not identify phone number from token'}, status=400)

    # 3. CLEAN UP PHONE (Handle formatting differences)
    # Firebase sends +2547..., Database might have 07...
    user = User.objects.filter(phone_number=verified_phone).first()

    if not user:
        # Try local format (07...)
        if verified_phone.startswith('+254'):
            local_format = '0' + verified_phone[4:]
            user = User.objects.filter(phone_number=local_format).first()

    if not user:
        return Response({'error': f'No student found with number {verified_phone}'}, status=404)

    if not new_password:
        return Response({'error': 'New password is required'}, status=400)

    # 4. RESET
    user.set_password(new_password)
    user.save()

    return Response({'message': 'Password reset successfully!'})

def upload_timetable(request):
    context = {}
    if request.method == 'POST' and request.FILES.get('myfile'):
        myfile = request.FILES['myfile']
        fs = FileSystemStorage()
        filename = fs.save(myfile.name, myfile)
        file_path = fs.path(filename)
        
        try:
            exams_data = process_exam_excel(file_path)
            Exam.objects.all().delete()
            
            exam_objects = [
                Exam(
                    course_code=item['course_code'],
                    title=item['title'],
                    date=item['date'], 
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
        
        
class StoryViewSet(viewsets.ModelViewSet):
    queryset = Story.objects.all()
    serializer_class = StorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        # Only show stories created in the last 24 hours
        time_threshold = timezone.now() - timezone.timedelta(hours=24)
        return Story.objects.filter(created_at__gte=time_threshold).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticatedOrReadOnly])
    def grouped(self, request):
        """Return stories grouped by user"""
        time_threshold = timezone.now() - timezone.timedelta(hours=24)
        stories = Story.objects.filter(created_at__gte=time_threshold).select_related('user').prefetch_related('viewed_by').order_by('-created_at')
        
        # Group by user
        from collections import OrderedDict
        grouped = OrderedDict()
        
        for story in stories:
            user_id = story.user.id
            if user_id not in grouped:
                grouped[user_id] = {
                    'user_id': user_id,
                    'username': story.user.username,
                    'user_avatar': request.build_absolute_uri(story.user.avatar.url) if story.user.avatar else None,
                    'has_unviewed': False,
                    'stories': []
                }
            
            # Check if this story is unviewed by current user
            if request.user.is_authenticated:
                if not story.viewed_by.filter(id=request.user.id).exists():
                    grouped[user_id]['has_unviewed'] = True
            
            # Serialize the story
            story_data = StorySerializer(story, context={'request': request}).data
            grouped[user_id]['stories'].append(story_data)
        
        return Response(list(grouped.values()))

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def mark_as_viewed(self, request, pk=None):
        story = self.get_object()
        user = request.user
        if not story.viewed_by.filter(id=user.id).exists():
            story.viewed_by.add(user)
        return Response({'status': 'viewed'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        story = self.get_object()
        user = request.user
        if story.liked_by.filter(id=user.id).exists():
            story.liked_by.remove(user)
            liked = False
        else:
            story.liked_by.add(user)
            liked = True
        return Response({'status': 'toggled', 'likes': story.total_likes, 'is_liked': liked})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def comment(self, request, pk=None):
        story = self.get_object()
        text = request.data.get('text')
        if not text:
            return Response({'error': 'Comment text required'}, status=400)
        comment = StoryComment.objects.create(story=story, user=request.user, text=text)
        serializer = StoryCommentSerializer(comment, context={'request': request})
        return Response(serializer.data, status=201)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def viewers(self, request, pk=None):
        """Get list of users who viewed this story"""
        story = self.get_object()
        
        # Only allow creator to see viewers
        if story.user != request.user:
            return Response({'error': 'Not authorized'}, status=403)
        
        viewers = story.viewed_by.all()
        serializer = StoryViewerSerializer(viewers, many=True, context={'request': request})
        
        return Response({
            'count': viewers.count(),
            'viewers': serializer.data
        })

class StoryCommentViewSet(viewsets.ModelViewSet):
    queryset = StoryComment.objects.all()
    serializer_class = StoryCommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        story_id = self.request.query_params.get('story_id')
        if story_id:
            return self.queryset.filter(story_id=story_id).order_by('created_at')
        return self.queryset

class CommunityPostViewSet(viewsets.ModelViewSet):
    queryset = CommunityPost.objects.all()
    serializer_class = CommunityPostSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        post = self.get_object() 
        user = request.user
        
        if post.liked_by.filter(id=user.id).exists():
            post.liked_by.remove(user)
            liked = False
        else:
            post.liked_by.add(user)
            liked = True
            
        return Response({'status': 'toggled', 'likes': post.total_likes, 'is_liked': liked})

class CommunityCommentViewSet(viewsets.ModelViewSet):
    queryset = CommunityComment.objects.all()
    serializer_class = CommunityCommentSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    def get_queryset(self):
        post_id = self.request.query_params.get('post_id')
        if post_id:
            return self.queryset.filter(post_id=post_id).order_by('created_at')
        return self.queryset        

def public_exam_search(request):
    exams = []
    query = request.GET.get('codes', '')
    
    if query:
        codes_list = [c.strip().upper() for c in query.split(',')]
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
        search_term = self.request.query_params.get('username')
        if search_term is not None:
            queryset = queryset.filter(
                Q(username__iexact=search_term) | 
                Q(admission_number__iexact=search_term)
            )
        return queryset
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def update_game_stats(self, request):
        """Update user's game statistics and award points"""
        user = request.user
        game_type = request.data.get('game_type')  # 'snake', 'binary', 'ram'
        points_earned = 0
        
        if game_type == 'snake':
            high_score = request.data.get('high_score', 0)
            score = request.data.get('score', 0)
            if high_score > user.snake_high_score:
                user.snake_high_score = high_score
            user.snake_games_played += 1
            # Award points based on score (1 point per 10 data packets)
            points_earned = score // 10
            
        elif game_type == 'binary':
            difficulty = request.data.get('difficulty')  # 'easy', 'medium', 'hard'
            won = request.data.get('won', False)
            draw = request.data.get('draw', False)
            
            user.binary_games_played += 1
            if won:
                if difficulty == 'easy':
                    user.binary_wins_easy += 1
                    points_earned = 10
                elif difficulty == 'medium':
                    user.binary_wins_medium += 1
                    points_earned = 20
                elif difficulty == 'hard':
                    user.binary_wins_hard += 1
                    points_earned = 30
            elif draw:
                points_earned = 5
                    
        elif game_type == 'ram':
            levels = request.data.get('levels_completed', 0)
            points_earned = request.data.get('points', 0) # RAM points are more complex, so we accept them from frontend
            user.ram_levels_completed = max(user.ram_levels_completed, levels)
            user.ram_games_played += 1
        
        user.points += points_earned
        user.save()  # This triggers achievement check via signals
        
        return Response({
            'message': f'Game stats updated. +{points_earned} points awarded.',
            'points_earned': points_earned,
            'total_points': user.points,
            'stats': {
                'snake_high_score': user.snake_high_score,
                'binary_wins_hard': user.binary_wins_hard,
                'binary_total_wins': user.binary_wins_easy + user.binary_wins_medium + user.binary_wins_hard,
            }
        })
    
@api_view(['GET'])
@permission_classes([AllowAny])
def check_update(request):
    latest_update = AppUpdate.objects.first()
    if latest_update:
        relative_url = latest_update.apk_file.url
        if not relative_url.startswith('http'):
            download_url = request.build_absolute_uri(relative_url)
        else:
            download_url = relative_url

        return Response({
            'version_code': latest_update.version_code,
            'download_url': download_url, 
            'release_notes': latest_update.release_notes,
            'is_mandatory': latest_update.is_mandatory
        })
    return Response({}, status=404) 

# ==========================================
# 🔒 SECURE CHANGE PASSWORD (ENFORCED)
# ==========================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])   # <--- 1. Enforce Login
def change_password(request):
    # 2. Use request.user (User identified by JWT)
    user = request.user 
    
    old_pass = request.data.get('old_password')
    new_pass = request.data.get('new_password')

    if not old_pass or not new_pass:
        return Response({'error': 'Missing fields'}, status=400)

    if not user.check_password(old_pass):
        return Response({'error': 'Wrong old password'}, status=400)

    user.set_password(new_pass)
    user.save()

    return Response({'message': 'Password updated successfully!'})

@api_view(['GET'])
@permission_classes([AllowAny])
def system_status(request):
    config, created = AppConfig.objects.get_or_create(id=1)
    serializer = AppConfigSerializer(config)
    return Response(serializer.data)
  
class ExamViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        codes_param = self.request.query_params.get('codes')
        
        if codes_param:
            codes_list = [c.strip().upper().replace(" ", "") for c in codes_param.split(',')]
            query = Q()
            for code in codes_list:
                if code: 
                    query |= Q(course_code__istartswith=code)
            
            return Exam.objects.filter(query).order_by('date')
            
        return Exam.objects.none()
        
class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [AllowAny] 

    def get_queryset(self):
        user_id = self.request.query_params.get('user_id')
        if user_id:
            return Task.objects.filter(user_id=user_id).order_by('due_date')
        return Task.objects.none()

    def perform_create(self, serializer):
        user_id = self.request.data.get('user_id')
        user = get_object_or_404(User, id=user_id)
        serializer.save(user=user)  

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all().order_by('date')
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def check_in(self, request, pk=None):
        event = self.get_object()
        user = request.user

        if event.checked_in_users.filter(id=user.id).exists():
            return Response({'message': 'Already checked in!'}, status=400)
        
        event.checked_in_users.add(user)
        user.points += 20
        user.save()

        return Response({
            'message': 'Check-in Successful! +20 Points', 
            'new_points': user.points
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def rsvp(self, request, pk=None):
        event = self.get_object()
        user = request.user
        
        try:
            rsvp, created = RSVP.objects.get_or_create(user=user, event=event)
            
            if not created:
                rsvp.delete()
                return Response({"status": "un-rsvped", "message": "RSVP cancelled"})
                
            return Response({"status": "rsvped", "message": "RSVP successful"})
            
        except Exception as e:
            return Response({"error": str(e)}, status=400)

    def get_queryset(self):
        attended_by = self.request.query_params.get('attended_by')
        if attended_by:
            return Event.objects.filter(checked_in_users__id=attended_by).order_by('-date')
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
    queryset = Promotion.objects.filter(is_active=True).order_by('-created_at')
    serializer_class = PromotionSerializer
    permission_classes = [AllowAny]    

class PaymentViewSet(viewsets.ReadOnlyModelViewSet): # Change to ReadOnlyModelViewSet
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only show the student THEIR OWN payments
        return Payment.objects.filter(student=self.request.user)


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
        secret_token = request.query_params.get('token')
        expected_token = os.getenv('PAYHERO_CALLBACK_SECRET')

        if secret_token != expected_token:
            print(f"SECURITY ALERT: Invalid Callback Token from {request.META.get('REMOTE_ADDR')}")
            return Response({"message": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

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
class AchievementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Achievement.objects.all()
    serializer_class = AchievementSerializer
    permission_classes = [permissions.IsAuthenticated]

class UserAchievementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserAchievementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserAchievement.objects.filter(user=self.request.user)

class StudyGroupViewSet(viewsets.ModelViewSet):
    queryset = StudyGroup.objects.all()
    serializer_class = StudyGroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'course_code', 'description']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        """Annotate queryset with member status for current user"""
        from django.db.models import Exists, OuterRef, Count
        
        user = self.request.user
        queryset = StudyGroup.objects.annotate(
            is_member=Exists(
                StudyGroup.objects.filter(
                    id=OuterRef('pk'),
                    members=user
                )
            ),
            member_count=Count('members')
        )
        return queryset

    def perform_create(self, serializer):
        group = serializer.save(creator=self.request.user)
        group.members.add(self.request.user)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        group = self.get_object()
        group.members.add(request.user)
        return Response({'status': 'joined'})

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        group = self.get_object()
        group.members.remove(request.user)
        return Response({'status': 'left'})

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        group = self.get_object()
        messages = group.messages.all()
        serializer = GroupMessageSerializer(messages, many=True)
        return Response(serializer.data)


# ============================================================================
# STUDY GROUP LANDING PAGE (for Universal Links)
# ============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def group_landing_page(request, group_id):
    """
    Landing page for study group deep links.
    If user has app installed, App Links will intercept and open app directly.
    Otherwise, shows group info with download/open app buttons.
    """
    try:
        group = StudyGroup.objects.get(id=group_id)
        
        context = {
            'group': group,
            'app_download_url': 'https://play.google.com/store/apps/details?id=com.dita.mobile',
            'app_store_url': 'https://apps.apple.com/app/dita/id123456789',
        }
        
        return render(request, 'api/group_landing.html', context)
    except StudyGroup.DoesNotExist:
        return render(request, 'api/group_not_found.html', status=404)
