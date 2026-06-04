import os
import hmac
import random
import requests
from datetime import timedelta
from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

from firebase_admin import auth
from rest_framework import generics, permissions, viewsets
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Achievement, User, UserAchievement, PhoneOTP
from .serializers import (
    AchievementSerializer,
    MyTokenObtainPairSerializer,
    RegisterSerializer,
    UserAchievementSerializer,
    UserSerializer,
)


class MyTokenObtainPairView(TokenObtainPairView):
    """
    Custom view for obtaining JWT tokens, using the MyTokenObtainPairSerializer
    to allow login with either username or admission number.
    """

    serializer_class = MyTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    """View for user registration, allowing new users to create an account."""

    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for managing user profiles, including retrieval and updating of user information."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Override the get_queryset method to allow filtering users by username or admission number using query parameters."""
        queryset = User.objects.all()
        search_term = self.request.query_params.get("username")
        if search_term is not None:
            queryset = queryset.filter(Q(username__iexact=search_term) | Q(admission_number__iexact=search_term))
        return queryset

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def update_game_stats(self, request):
        """Custom action to update user game statistics and points based on the game type and results."""
        user = request.user
        game_type = request.data.get("game_type")
        points_earned = 0

        # Update stats and calculate points based on the game type and results
        if game_type == "snake":
            high_score = request.data.get("high_score", 0)
            score = request.data.get("score", 0)
            if high_score > user.snake_high_score:
                user.snake_high_score = high_score
            user.snake_games_played += 1
            points_earned = score // 10

        # Update stats and calculate points for binary game based on difficulty and results
        elif game_type == "binary":
            difficulty = request.data.get("difficulty")
            won = request.data.get("won", False)
            draw = request.data.get("draw", False)
            user.binary_games_played += 1
            if won:
                if difficulty == "easy":
                    user.binary_wins_easy += 1
                    points_earned = 10
                elif difficulty == "medium":
                    user.binary_wins_medium += 1
                    points_earned = 20
                elif difficulty == "hard":
                    user.binary_wins_hard += 1
                    points_earned = 30
            elif draw:
                points_earned = 5

        # Update stats and calculate points for RAM game based on levels completed and results
        elif game_type == "ram":
            levels = request.data.get("levels_completed", 0)
            points_earned = request.data.get("points", 0)
            user.ram_levels_completed = max(user.ram_levels_completed, levels)
            user.ram_games_played += 1

        # Prevent absurd point injections (Cheat Prevention)
        points_earned = min(max(0, int(points_earned)), 200) 
        
        user.points += points_earned
        user.save()

        return Response(
            {
                "message": f"Game stats updated. +{points_earned} points awarded.",
                "points_earned": points_earned,
                "total_points": user.points,
                "stats": {
                    "snake_high_score": user.snake_high_score,
                    "binary_wins_hard": user.binary_wins_hard,
                    "binary_total_wins": user.binary_wins_easy + user.binary_wins_medium + user.binary_wins_hard,
                },
            }
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_leaderboard(request):
    """API view to retrieve the top 20 students based on their points, including their username, program, points, and avatar URL."""
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
    """API view to reset a user's password using their phone number, with Firebase token verification for security."""
    new_password = request.data.get("new_password")
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return Response({"error": "Missing or Invalid Firebase Token"}, status=401)

    id_token = auth_header.split(" ")[1]
    verified_phone = None
    try:
        decoded_token = auth.verify_id_token(id_token)
        verified_phone = decoded_token.get("phone_number")
    except Exception as e:
        print(f"Token Verification Failed: {e}")
        return Response({"error": "Invalid or Expired Security Token"}, status=401)

    if not verified_phone:
        return Response({"error": "Could not identify phone number from token"}, status=400)

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


def format_phone_number(phone):
    """Formats a phone number to E.164 international format (+254...) for Kenya."""
    phone = phone.strip()
    if phone.startswith('+'):
        return phone
    if phone.startswith('0'):
        return '+254' + phone[1:]
    if len(phone) == 9 and (phone.startswith('7') or phone.startswith('1')):
        return '+254' + phone
    return phone


def get_user_by_phone(phone_number):
    """Finds a user by phone number using formatted international or local zero format."""
    formatted = format_phone_number(phone_number)
    user = User.objects.filter(phone_number=formatted).first()
    if not user and formatted.startswith("+254"):
        local_format = "0" + formatted[4:]
        user = User.objects.filter(phone_number=local_format).first()
    return user


def send_otp_sms(phone_number, otp):
    """Sends an OTP code via Africa's Talking SMS API."""
    api_key = os.environ.get("AFRICAS_TALKING_API_KEY")
    username = os.environ.get("AFRICAS_TALKING_USERNAME", "sandbox")
    sender_id = os.environ.get("AFRICAS_TALKING_SENDER_ID")
    is_sandbox = os.environ.get("AFRICAS_TALKING_IS_SANDBOX", "True").lower() == "true"

    if not api_key:
        print("Warning: AFRICAS_TALKING_API_KEY not set. OTP sending logged locally.")
        print(f"SMS OTP for {phone_number}: {otp}")
        # In development environment without API keys, mock success to allow testing/flow completion
        return True

    url = (
        "https://api.sandbox.africastalking.com/version1/messaging"
        if is_sandbox
        else "https://api.africastalking.com/version1/messaging"
    )

    headers = {
        "apiKey": api_key,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }

    message = f"Your DITA password reset code is {otp}. Valid for 10 minutes."

    data = {
        "username": username,
        "to": phone_number,
        "message": message,
    }
    if sender_id:
        data["from"] = sender_id

    try:
        response = requests.post(url, headers=headers, data=data, timeout=15)
        if response.status_code in [200, 201]:
            print(f"Africa's Talking SMS API success: {response.json()}")
            return True
        else:
            print(f"Africa's Talking SMS API failed with status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"Exception while sending SMS via Africa's Talking: {e}")
        return False


class OTPRequestThrottle(AnonRateThrottle):
    """Custom throttle to limit OTP request requests to 5 per hour per IP."""
    rate = '5/hour'


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([OTPRequestThrottle])
def request_otp(request):
    """API view to request a password reset OTP, sent via Africa's Talking SMS."""
    phone_number = request.data.get("phone_number")
    if not phone_number:
        return Response({"error": "Phone number is required"}, status=400)

    phone_number = phone_number.strip()
    user = get_user_by_phone(phone_number)
    if not user:
        return Response({"error": "No student found with this phone number"}, status=404)

    # Format recipient for Africa's Talking
    formatted_recipient = format_phone_number(phone_number)

    # Check 60-second cooldown per phone number to prevent SMS flooding
    existing_otp = PhoneOTP.objects.filter(phone_number=formatted_recipient).first()
    if existing_otp and timezone.now() < existing_otp.created_at + timedelta(seconds=60):
        return Response(
            {"error": "Please wait 60 seconds before requesting another code."},
            status=429
        )

    # Generate a random 6-digit OTP
    otp = str(random.randint(100000, 999999))

    # Send the OTP via Africa's Talking
    success = send_otp_sms(formatted_recipient, otp)

    if not success:
        return Response({"error": "Failed to send SMS. Please try again later."}, status=500)

    # Save or update the OTP in the database (resetting failed attempts to 0)
    PhoneOTP.objects.update_or_create(
        phone_number=formatted_recipient,
        defaults={"otp": otp, "created_at": timezone.now(), "failed_attempts": 0}
    )

    return Response({"message": "OTP sent successfully via SMS!"})


@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password_otp(request):
    """API view to verify the OTP and update the user's password with strength validation."""
    phone_number = request.data.get("phone_number")
    otp = request.data.get("otp")
    new_password = request.data.get("new_password")

    if not phone_number or not otp or not new_password:
        return Response({"error": "Phone number, OTP, and new password are required"}, status=400)

    phone_number = phone_number.strip()
    otp = otp.strip()
    new_password = new_password.strip()

    formatted_phone = format_phone_number(phone_number)

    otp_record = PhoneOTP.objects.filter(phone_number=formatted_phone).first()
    if not otp_record:
        return Response({"error": "No OTP requested for this phone number"}, status=400)

    # Check expiration (10 minutes)
    if timezone.now() > otp_record.created_at + timedelta(minutes=10):
        otp_record.delete()
        return Response({"error": "OTP has expired. Please request a new one."}, status=400)

    user = get_user_by_phone(formatted_phone)
    if not user:
        return Response({"error": "No student found with this phone number"}, status=404)

    # Verify match and handle brute-force protection
    if otp_record.otp != otp:
        otp_record.failed_attempts += 1
        if otp_record.failed_attempts >= 3:
            otp_record.delete()
            return Response(
                {"error": "Too many failed attempts. This code is now invalid. Please request a new one."},
                status=400
            )
        else:
            otp_record.save()
            remaining = 3 - otp_record.failed_attempts
            return Response(
                {"error": f"Invalid OTP. {remaining} attempt(s) remaining."},
                status=400
            )

    # Validate new password strength
    try:
        validate_password(new_password, user)
    except ValidationError as e:
        return Response({"error": " ".join(e.messages)}, status=400)

    # Update password
    user.set_password(new_password)
    user.save()

    # Clean up OTP record
    otp_record.delete()

    return Response({"message": "Password reset successfully!"})




@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    """API view to allow authenticated users to change their password by providing the old password and a new password, with validation for security."""
    user = request.user
    old_pass = request.data.get("old_password")
    new_pass = request.data.get("new_password")

    if not old_pass or not new_pass:
        return Response({"error": "Missing fields"}, status=400)
    if not user.check_password(old_pass):
        return Response({"error": "Wrong old password"}, status=400)

    user.set_password(new_pass)
    user.save()
    return Response({"message": "Password updated successfully!"})


class AchievementViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for retrieving achievement information, allowing users to view available achievements and their details."""

    queryset = Achievement.objects.all()
    serializer_class = AchievementSerializer
    permission_classes = [permissions.IsAuthenticated]


class UserAchievementViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for retrieving the achievements earned by the authenticated user, including details of each achievement."""

    serializer_class = UserAchievementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Override the get_queryset method to return only the achievements earned by the authenticated user."""
        return UserAchievement.objects.filter(user=self.request.user)


@api_view(["GET"])
@permission_classes([AllowAny])
def verify_voter(request):
    """
    Internal API view to verify if a student is a user of the DITA App by admission number.
    Uses an internal key for security.
    """
    internal_key = os.environ.get("INTERNAL_API_KEY")
    client_key = request.headers.get("X-Internal-Key")
    
    if not internal_key or not client_key or not hmac.compare_digest(client_key, internal_key):
        return Response({"error": "Forbidden"}, status=403)

    admission_number = request.query_params.get("admission_number")
    if not admission_number:
        return Response({"error": "Admission number is required"}, status=400)

    # We check if the user exists in the app database
    user = User.objects.filter(admission_number__iexact=admission_number).first()

    if not user:
        return Response({"is_user": False, "reason": "not_found"})

    return Response({
        "is_user": True,
        "username": user.username,
        "admission_number": user.admission_number
    })
