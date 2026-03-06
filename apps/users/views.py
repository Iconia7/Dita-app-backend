from django.db.models import Q
from rest_framework import generics, permissions, viewsets
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView
from firebase_admin import auth

from .models import Achievement, User, UserAchievement
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
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

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
