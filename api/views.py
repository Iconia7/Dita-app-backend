import os
import json
import logging
from datetime import timedelta, datetime
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

import firebase_admin
from firebase_admin import auth, credentials
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView

# DRF Imports
from api.permissions import IsOwnerOrReadOnly
from config.utils import process_exam_excel

# Local Imports
from .models import (
    RSVP, Achievement, Announcement, AppConfig, AppUpdate,
    CommunityComment, CommunityPost, Event, Exam, Payment,
    Promotion, Resource, Story, StoryComment, StudyGroup,
    Task, User, UserAchievement,
)
from .payhero_utils import initiate_payhero_push
from .mpesa_utils import initiate_stk_push
from .serializers import (
    AchievementSerializer, AnnouncementSerializer, AppConfigSerializer,
    CommunityCommentSerializer, CommunityPostSerializer, EventSerializer,
    ExamSerializer, GroupMessageSerializer, MyTokenObtainPairSerializer,
    PaymentSerializer, PromotionSerializer, RegisterSerializer,
    ResourceSerializer, StoryCommentSerializer, StorySerializer,
    StoryViewerSerializer, StudyGroupSerializer, TaskSerializer,
    UserAchievementSerializer, UserSerializer,
)
from .portal_scraper import scrape_portal

# ==========================================
# 🔥 FIREBASE INITIALIZATION
# ==========================================
try:
    if not firebase_admin._apps:
        cred_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
        if not cred_path:
            if os.environ.get("RENDER"):
                cred_path = "/etc/secrets/serviceAccountKey.json"
            else:
                cred_path = os.path.join(settings.BASE_DIR, "config", "serviceAccountKey.json")
                if not os.path.exists(cred_path):
                    cred_path = os.path.join(settings.BASE_DIR, "serviceAccountKey.json")
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info(f"Firebase Admin SDK Initialized from: {cred_path}")
        else:
            logger.warning(f"Service Account Key not found at: {cred_path}")
except Exception as e:
    logger.error(f"Firebase Init Warning: {e}")

# ==========================================
#  STANDARD VIEWSETS (CRUD)
# ==========================================

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

@api_view(["GET"])
@permission_classes([AllowAny])
def get_leaderboard(request):
    top_students = User.objects.filter(points__gt=0).order_by("-points")[:20]
    data = []
    for user in top_students:
        avatar_url = user.avatar.url if user.avatar else None
        if avatar_url and not avatar_url.startswith("http"):
            avatar_url = request.build_absolute_uri(avatar_url)
        data.append({"username": user.username, "program": user.program, "points": user.points, "avatar": avatar_url})
    return Response(data)

@api_view(["POST"])
@permission_classes([AllowAny])
@authentication_classes([])
def reset_password_phone(request):
    new_password = request.data.get("new_password")
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return Response({"error": "Missing or Invalid Firebase Token"}, status=401)
    id_token = auth_header.split(" ")[1]
    try:
        decoded_token = auth.verify_id_token(id_token)
        verified_phone = decoded_token.get("phone_number")
    except Exception as e:
        return Response({"error": "Invalid or Expired Security Token"}, status=401)
    user = User.objects.filter(phone_number=verified_phone).first()
    if not user and verified_phone.startswith("+254"):
        local_format = "0" + verified_phone[4:]
        user = User.objects.filter(phone_number=local_format).first()
    if not user:
        return Response({"error": f"No student found with number {verified_phone}"}, status=404)
    if not new_password:
        return Response({"error": "New password is required"}, status=400)
    user.set_password(new_password)
    user.save()
    return Response({"message": "Password reset successfully!"})

def upload_timetable(request):
    context = {}
    if request.method == "POST" and request.FILES.get("myfile"):
        myfile = request.FILES["myfile"]
        fs = FileSystemStorage()
        filename = fs.save(myfile.name, myfile)
        file_path = fs.path(filename)
        try:
            exams_data = process_exam_excel(file_path)
            Exam.objects.all().delete()
            exam_objects = [
                Exam(
                    course_code=item["course_code"],
                    title=item["title"],
                    date=item["date"],
                    end_time=item["end_time"],
                    venue=item["venue"],
                    duration_hours=item["duration_hours"],
                )
                for item in exams_data
            ]
            Exam.objects.bulk_create(exam_objects)
            context["success"] = f"Success! Imported {len(exam_objects)} exams."
        except Exception as e:
            context["error"] = f"Error: {str(e)}"
        fs.delete(filename)
    return render(request, "upload.html", context)

class StoryViewSet(viewsets.ModelViewSet):
    queryset = Story.objects.all()
    serializer_class = StorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    def get_queryset(self):
        time_threshold = timezone.now() - timezone.timedelta(hours=24)
        return Story.objects.filter(created_at__gte=time_threshold).order_by("-created_at")
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticatedOrReadOnly])
    def grouped(self, request):
        time_threshold = timezone.now() - timezone.timedelta(hours=24)
        stories = Story.objects.filter(created_at__gte=time_threshold).select_related("user").prefetch_related("viewed_by").order_by("-created_at")
        grouped = {}
        for story in stories:
            user_id = story.user.id
            if user_id not in grouped:
                grouped[user_id] = {
                    "user_id": user_id,
                    "username": story.user.username,
                    "user_avatar": request.build_absolute_uri(story.user.avatar.url) if story.user.avatar else None,
                    "has_unviewed": False,
                    "stories": [],
                }
            if request.user.is_authenticated:
                if not story.viewed_by.filter(id=request.user.id).exists():
                    grouped[user_id]["has_unviewed"] = True
            story_data = StorySerializer(story, context={"request": request}).data
            grouped[user_id]["stories"].append(story_data)
        return Response(list(grouped.values()))

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def mark_as_viewed(self, request, pk=None):
        story = self.get_object()
        if not story.viewed_by.filter(id=request.user.id).exists():
            story.viewed_by.add(request.user)
        return Response({"status": "viewed"})

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        story = self.get_object()
        if story.liked_by.filter(id=request.user.id).exists():
            story.liked_by.remove(request.user)
            liked = False
        else:
            story.liked_by.add(request.user)
            liked = True
        return Response({"status": "toggled", "likes": story.total_likes, "is_liked": liked})

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def comment(self, request, pk=None):
        story = self.get_object()
        text = request.data.get("text")
        if not text: return Response({"error": "Comment text required"}, status=400)
        comment = StoryComment.objects.create(story=story, user=request.user, text=text)
        return Response(StoryCommentSerializer(comment, context={"request": request}).data, status=201)

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def viewers(self, request, pk=None):
        story = self.get_object()
        if story.user != request.user: return Response({"error": "Not authorized"}, status=403)
        viewers = story.viewed_by.all()
        return Response({"count": viewers.count(), "viewers": StoryViewerSerializer(viewers, many=True, context={"request": request}).data})

class StoryCommentViewSet(viewsets.ModelViewSet):
    queryset = StoryComment.objects.all()
    serializer_class = StoryCommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    def perform_create(self, serializer): serializer.save(user=self.request.user)
    def get_queryset(self):
        story_id = self.request.query_params.get("story_id")
        return self.queryset.filter(story_id=story_id).order_by("created_at") if story_id else self.queryset

class CommunityPostViewSet(viewsets.ModelViewSet):
    queryset = CommunityPost.objects.all()
    serializer_class = CommunityPostSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    def perform_create(self, serializer): serializer.save(user=self.request.user)
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        post = self.get_object()
        if post.liked_by.filter(id=request.user.id).exists():
            post.liked_by.remove(request.user)
            liked = False
        else:
            post.liked_by.add(request.user)
            liked = True
        return Response({"status": "toggled", "likes": post.total_likes, "is_liked": liked})

class CommunityCommentViewSet(viewsets.ModelViewSet):
    queryset = CommunityComment.objects.all()
    serializer_class = CommunityCommentSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    def perform_create(self, serializer): serializer.save(user=self.request.user)
    def get_queryset(self):
        post_id = self.request.query_params.get("post_id")
        return self.queryset.filter(post_id=post_id).order_by("created_at") if post_id else self.queryset

def public_exam_search(request):
    exams = []
    query = request.GET.get("codes", "")
    if query:
        codes_list = [c.strip().upper().replace(" ", "") for c in query.split(",")]
        db_query = Q()
        for code in codes_list:
            if code: db_query |= Q(course_code__istartswith=code)
        if db_query: exams = Exam.objects.filter(db_query).order_by("date")
    return render(request, "exam_search.html", {"exams": exams})

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]
    def get_queryset(self):
        queryset = User.objects.all()
        search_term = self.request.query_params.get("username")
        if search_term: queryset = queryset.filter(Q(username__iexact=search_term) | Q(admission_number__iexact=search_term))
        return queryset
    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def update_game_stats(self, request):
        user = request.user
        game_type = request.data.get("game_type")
        points_earned = 0
        if game_type == "snake":
            high_score = request.data.get("high_score", 0)
            score = request.data.get("score", 0)
            if high_score > user.snake_high_score: user.snake_high_score = high_score
            user.snake_games_played += 1
            points_earned = score // 10
        elif game_type == "binary":
            difficulty = request.data.get("difficulty")
            won, draw = request.data.get("won", False), request.data.get("draw", False)
            user.binary_games_played += 1
            if won:
                if difficulty == "easy": user.binary_wins_easy += 1; points_earned = 10
                elif difficulty == "medium": user.binary_wins_medium += 1; points_earned = 20
                elif difficulty == "hard": user.binary_wins_hard += 1; points_earned = 30
            elif draw: points_earned = 5
        elif game_type == "ram":
            levels = request.data.get("levels_completed", 0)
            points_earned = request.data.get("points", 0)
            user.ram_levels_completed = max(user.ram_levels_completed, levels)
            user.ram_games_played += 1
        user.points += points_earned
        user.save()
        return Response({"message": f"Game stats updated. +{points_earned} points awarded."})

@api_view(["GET"])
@permission_classes([AllowAny])
def check_update(request):
    latest_update = AppUpdate.objects.first()
    if latest_update:
        download_url = request.build_absolute_uri(latest_update.apk_file.url) if not latest_update.apk_file.url.startswith("http") else latest_update.apk_file.url
        return Response({"version_code": latest_update.version_code, "download_url": download_url, "release_notes": latest_update.release_notes, "is_mandatory": latest_update.is_mandatory})
    return Response({}, status=404)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    user = request.user
    old_pass, new_pass = request.data.get("old_password"), request.data.get("new_password")
    if not old_pass or not new_pass: return Response({"error": "Missing fields"}, status=400)
    if not user.check_password(old_pass): return Response({"error": "Wrong old password"}, status=400)
    user.set_password(new_pass); user.save()
    return Response({"message": "Password updated successfully!"})

@api_view(["GET"])
@permission_classes([AllowAny])
def system_status(request):
    config, _ = AppConfig.objects.get_or_create(id=1)
    return Response(AppConfigSerializer(config).data)

class ExamViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer
    permission_classes = [AllowAny]
    def get_queryset(self):
        codes_param = self.request.query_params.get("codes")
        if codes_param:
            codes_list = [c.strip().upper().replace(" ", "") for c in codes_param.split(",")]
            query = Q()
            for code in codes_list:
                if code: query |= Q(course_code__istartswith=code)
            return Exam.objects.filter(query).order_by("date")
        return Exam.objects.none()

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [AllowAny]
    def get_queryset(self):
        user_id = self.request.query_params.get("user_id")
        return Task.objects.filter(user_id=user_id).order_by("due_date") if user_id else Task.objects.none()
    def perform_create(self, serializer):
        user = get_object_or_404(User, id=self.request.data.get("user_id"))
        serializer.save(user=user)

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all().order_by("date")
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def check_in(self, request, pk=None):
        event = self.get_object()
        if event.checked_in_users.filter(id=request.user.id).exists(): return Response({"message": "Already checked in!"}, status=400)
        event.checked_in_users.add(request.user)
        request.user.points += 20; request.user.save()
        return Response({"message": "Check-in Successful! +20 Points"})
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def rsvp(self, request, pk=None):
        event = self.get_object()
        rsvp, created = RSVP.objects.get_or_create(user=request.user, event=event)
        if not created: rsvp.delete(); return Response({"status": "un-rsvped"})
        return Response({"status": "rsvped"})
    def get_queryset(self):
        attended_by = self.request.query_params.get("attended_by")
        return Event.objects.filter(checked_in_users__id=attended_by).order_by("-date") if attended_by else self.queryset

class ResourceViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.filter(is_active=True).order_by("-date_posted")
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class PromotionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Promotion.objects.filter(is_active=True).order_by("-created_at")
    serializer_class = PromotionSerializer
    permission_classes = [AllowAny]

class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self): return Payment.objects.filter(student=self.request.user)

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
        phone = request.data.get("phone")
        user_id = request.data.get("user_id")
        amount = 200
        if phone and phone.startswith('0'): phone = '254' + phone[1:]
        elif phone and phone.startswith('+'): phone = phone[1:]
        if not phone or not user_id: return Response({"error": "Phone and User ID are required."}, status=400)
        user = get_object_or_404(User, id=user_id)
        ref = f"dita-pay-{user.id}-{int(timezone.now().timestamp())}"
        Payment.objects.create(student=user, phone_number=phone, amount=amount, external_reference=ref, status="pending")
        resp = initiate_stk_push(phone, amount, ref)
        if not resp: return Response({"error": "Failed to initiate M-Pesa STK push."}, status=500)
        return Response({"message": "STK push sent. Enter PIN."}, status=200)

class MpesaCallbackView(APIView):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        # Validate Secret Token
        token = request.query_params.get("token")
        expected_token = os.getenv("MPESA_CALLBACK_SECRET")
        if not token or token != expected_token:
            logger.error(f"UNAUTHORIZED: Callback attempt with invalid token: {token}")
            return Response({"ResultCode": 1, "ResultDesc": "Unauthorized"}, status=401)

        data = request.data.get("Body", {}).get("stkCallback", {})
        code = data.get("ResultCode")
        meta = data.get("CallbackMetadata", {}).get("Item", [])
        receipt, phone = None, None
        for item in meta:
            if item.get("Name") == "MpesaReceiptNumber": receipt = item.get("Value")
            if item.get("Name") == "PhoneNumber": phone = item.get("Value")
        if code == 0:
            payment = Payment.objects.filter(phone_number__contains=str(phone), status="pending").last()
            if payment:
                payment.status = "completed"; payment.mpesa_receipt = receipt; payment.save()
                student = payment.student
                now = timezone.now()
                student.membership_expiry = (student.membership_expiry or now) + timedelta(days=120)
                student.save()
                logger.info(f"SUCCESS: Membership extended for {student.username}")
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

class AchievementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Achievement.objects.all(); serializer_class = AchievementSerializer; permission_classes = [IsAuthenticated]

class UserAchievementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserAchievementSerializer; permission_classes = [IsAuthenticated]
    def get_queryset(self): return UserAchievement.objects.filter(user=self.request.user)

class StudyGroupViewSet(viewsets.ModelViewSet):
    queryset = StudyGroup.objects.all(); serializer_class = StudyGroupSerializer; permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "course_code", "description"]
    def get_queryset(self):
        from django.db.models import Count, Exists, OuterRef
        queryset = StudyGroup.objects.annotate(is_member=Exists(StudyGroup.objects.filter(id=OuterRef("pk"), members=self.request.user)), member_count=Count("members"))
        return queryset
    def perform_create(self, serializer): serializer.save(creator=self.request.user).members.add(self.request.user)
    @action(detail=True, methods=["post"])
    def join(self, request, pk=None): self.get_object().members.add(request.user); return Response({"status": "joined"})
    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None): self.get_object().members.remove(request.user); return Response({"status": "left"})
    @action(detail=True, methods=["get"])
    def messages(self, request, pk=None): return Response(GroupMessageSerializer(self.get_object().messages.all(), many=True).data)

@api_view(["GET"])
@permission_classes([AllowAny])
def group_landing_page(request, group_id):
    group = get_object_or_404(StudyGroup, id=group_id)
    return render(request, "api/group_landing.html", {"group": group})

@api_view(["GET"])
@permission_classes([AllowAny])
def verify_voter(request):
    if request.headers.get("X-Internal-Key") != os.environ.get("INTERNAL_API_KEY", "DITA_Secur3_Internal_Bridge_2024"): return Response({"error": "Forbidden"}, status=403)
    user = User.objects.filter(email=request.query_params.get("email")).first()
    if not user: return Response({"is_member": False, "reason": "not_found"})
    return Response({"is_member": user.is_active_member, "reason": "active" if user.is_active_member else "expired", "username": user.username})

@csrf_exempt
def portal_sync_exams(request):
    if request.method != 'POST': return JsonResponse({"error": "POST method required"}, status=405)
    data = json.loads(request.body) if request.body else request.POST
    adm, pwd = data.get('admission_number'), data.get('password')
    if not adm or not pwd: return JsonResponse({"error": "Required fields missing"}, status=400)
    codes = scrape_portal(adm, pwd)
    if isinstance(codes, dict) and "error" in codes: return JsonResponse(codes, status=400)
    unit_codes = [c.strip().upper().replace(' ', '') for c in codes]
    matched = ExamSerializer(Exam.objects.filter(course_code__in=unit_codes), many=True).data
    return JsonResponse({"count": len(matched), "codes_found": list(set(unit_codes)), "exams": matched})
