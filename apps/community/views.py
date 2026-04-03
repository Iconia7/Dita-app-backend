from collections import OrderedDict

from django.utils import timezone

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.permissions import IsOwnerOrReadOnly

from .models import CommunityComment, CommunityPost, Story, StoryComment
from .serializers import (
    CommunityCommentSerializer,
    CommunityPostSerializer,
    StoryCommentSerializer,
    StorySerializer,
    StoryViewerSerializer,
)


class StoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing stories, including listing, retrieving, creating, updating, and deleting stories, as well as custom actions for marking stories as viewed, liking stories, adding comments, and retrieving viewers of a story.
    This viewset also ensures that only authenticated users can create stories and that users can only modify their own stories.
    """

    queryset = Story.objects.all()
    serializer_class = StorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """
        Override the get_queryset method to filter stories based on their creation time, returning only stories that were created within the last 24 hours.
        This ensures that expired stories are not included in the queryset and that the most recent stories are returned first.
        """
        time_threshold = timezone.now() - timezone.timedelta(hours=24)
        return Story.objects.filter(created_at__gte=time_threshold).order_by("-created_at")

    def perform_create(self, serializer):
        """
        Override the perform_create method to automatically associate the story with the authenticated user when a new story is created.
        This ensures that the user field of the Story model is set to the current user without requiring it to be included in the request data.
        """
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticatedOrReadOnly])
    def grouped(self, request):
        """
        Custom action to retrieve stories grouped by user, including information about whether the current user has unviewed stories from each user.
        This method retrieves stories created within the last 24 hours, groups them by user, and checks if the authenticated user has viewed each story to determine if there are any unviewed stories for that user.
        The response includes the grouped stories along with user information and unviewed status.
        """
        time_threshold = timezone.now() - timezone.timedelta(hours=24)
        stories = (
            Story.objects.filter(created_at__gte=time_threshold)
            .select_related("user")
            .prefetch_related("viewed_by")
            .order_by("-created_at")
        )
        grouped = OrderedDict()
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
        """
        Custom action to mark a story as viewed by the authenticated user.
        This method retrieves the story object based on the provided primary key and adds the user to the story's viewed_by ManyToMany relationship
        if they haven't already viewed it,then returns a response indicating that the story has been marked as viewed.
        """
        story = self.get_object()
        if not story.viewed_by.filter(id=request.user.id).exists():
            story.viewed_by.add(request.user)
        return Response({"status": "viewed"})

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        """
        Custom action to toggle the like status of a story for the authenticated user.
        This method checks if the user has already liked the story and either removes the like or adds it accordingly, then returns the updated like count and like status.
        """
        story = self.get_object()
        user = request.user
        if story.liked_by.filter(id=user.id).exists():
            story.liked_by.remove(user)
            liked = False
        else:
            story.liked_by.add(user)
            liked = True
        return Response({"status": "toggled", "likes": story.total_likes, "is_liked": liked})

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def comment(self, request, pk=None):
        """
        Custom action to add a comment to a story. This method retrieves the story object based on the provided primary key, extracts the comment text from the request data, and creates a new StoryComment instance associated with the story and the authenticated user.
        The newly created comment is then serialized and returned in the response with a status code of 201 (Created). If the comment text is not provided in the request, an error response with a status code of 400 (Bad Request) is returned.
        """
        story = self.get_object()
        text = request.data.get("text")
        if not text:
            return Response({"error": "Comment text required"}, status=400)
        comment = StoryComment.objects.create(story=story, user=request.user, text=text)
        serializer = StoryCommentSerializer(comment, context={"request": request})
        return Response(serializer.data, status=201)

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def viewers(self, request, pk=None):
        """
        Custom action to retrieve a list of users who have viewed the story, including their usernames and avatars.
        This action checks if the requesting user is the owner of the story before returning the viewer information, ensuring that only the story owner can access this data.
        """
        story = self.get_object()
        if story.user != request.user:
            return Response({"error": "Not authorized"}, status=403)
        viewers = story.viewed_by.all()
        serializer = StoryViewerSerializer(viewers, many=True, context={"request": request})
        return Response({"count": viewers.count(), "viewers": serializer.data})


class StoryCommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing comments on stories, including listing, retrieving, creating, updating, and deleting comments, as well as filtering comments by related story ID.
    This viewset also ensures that only authenticated users can create comments and that users can only modify their own comments.
    """

    queryset = StoryComment.objects.all()
    serializer_class = StoryCommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        """
        Override the perform_create method to automatically associate the comment with the authenticated user when a new comment is created.
        This ensures that the user field of the StoryComment model is set to the current user without requiring it to be included in the request data.
        """
        serializer.save(user=self.request.user)

    def get_queryset(self):
        """
        Override the get_queryset method to allow filtering comments by related story ID using query parameters.
        If a story_id is provided in the query parameters, the queryset will be filtered to include only comments related to that specific story, ordered by creation time. If no story_id is provided, all comments will be returned.
        """
        story_id = self.request.query_params.get("story_id")
        if story_id:
            return self.queryset.filter(story_id=story_id).order_by("created_at")
        return self.queryset


class CommunityPostViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing community posts, including listing, retrieving, creating, updating, and deleting posts, as well as custom actions for liking posts.
    This viewset also ensures that only authenticated users can create posts and that users can only modify their own posts.
    """

    queryset = CommunityPost.objects.all()
    serializer_class = CommunityPostSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        """Override the perform_create method to automatically associate the post with the authenticated user when a new post is created. This ensures that the user field of the CommunityPost model is set to the current user without requiring it to be included in the request data."""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        """
        Custom action to toggle the like status of a post for the authenticated user.
        This method checks if the user has already liked the post and either removes the like or adds it accordingly, then returns the updated like count and like status.
        """
        post = self.get_object()
        user = request.user
        if post.liked_by.filter(id=user.id).exists():
            post.liked_by.remove(user)
            liked = False
        else:
            post.liked_by.add(user)
            liked = True
        return Response({"status": "toggled", "likes": post.total_likes, "is_liked": liked})


class CommunityCommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing community comments, including listing, retrieving, creating, updating, and deleting comments, as well as filtering comments by related post ID.
    This viewset also ensures that only authenticated users can create comments and that users can only modify their own comments.
    """

    queryset = CommunityComment.objects.all()
    serializer_class = CommunityCommentSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        """Override the perform_create method to automatically associate the comment with the authenticated user when a new comment is created. This ensures that the user field of the CommunityComment model is set to the current user without requiring it to be included in the request data."""
        serializer.save(user=self.request.user)

    def get_queryset(self):
        """
        Override the get_queryset method to allow filtering comments by related post ID using query parameters.
        If a post_id is provided in the query parameters, the queryset will be filtered to include only comments related to that specific post, ordered by creation time. If no post_id is provided, all comments will be returned.
        """
        post_id = self.request.query_params.get("post_id")
        if post_id:
            return self.queryset.filter(post_id=post_id).order_by("created_at")
        return self.queryset
