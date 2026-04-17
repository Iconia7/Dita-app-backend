from django.core.files.storage import FileSystemStorage
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from apps.users.models import User
from config.utils import process_exam_excel
from .models import AppConfig, AppUpdate, Exam, Resource, Task
from .serializers import (
    AppConfigSerializer, AppUpdateSerializer, ExamSerializer,
    ResourceSerializer, TaskSerializer
)
from .utils import scrape_portal


class ExamViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for listing and retrieving exams, with support for filtering by course codes provided as query parameters."""

    queryset = Exam.objects.all()
    serializer_class = ExamSerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Override the get_queryset method to allow filtering exams by course codes provided as query parameters."""
        codes_param = self.request.query_params.get("codes")
        if codes_param:
            codes_list = [c.strip().upper().replace(" ", "") for c in codes_param.split(",")]
            query = Q()
            for code in codes_list:
                if code:
                    query |= Q(course_code__istartswith=code)
            return Exam.objects.filter(query).order_by("date")
        return Exam.objects.none()


class TaskViewSet(viewsets.ModelViewSet):
    """ViewSet for managing tasks, including listing, retrieving, creating, updating, and deleting tasks."""

    serializer_class = TaskSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Override the get_queryset method to allow filtering tasks by user ID using query parameters."""
        user_id = self.request.query_params.get("user_id")
        if user_id:
            return Task.objects.filter(user_id=user_id).order_by("due_date")
        return Task.objects.none()

    def perform_create(self, serializer):
        """Override the perform_create method to associate the created task with the user specified in the request data."""
        user_id = self.request.data.get("user_id")
        user = get_object_or_404(User, id=user_id)
        serializer.save(user=user)


class ResourceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing resources, including listing, retrieving, creating, updating, and deleting resources.
    The viewset allows any user to read resources but restricts write operations to authenticated users only.
    """

    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


def upload_timetable(request):
    """
    View function to handle the upload of an Excel (.xlsx) or Word (.docx) file containing exam timetable data.
    - Excel files: Clears the entire Exam database and imports fresh data.
    - Word files (Nursing): Appends the new exams to the existing database without clearing.
    """
    context = {}
    if request.method == "POST" and request.FILES.get("myfile"):
        myfile = request.FILES["myfile"]
        filename_lower = myfile.name.lower()
        
        fs = FileSystemStorage()
        filename = fs.save(myfile.name, myfile)
        file_path = fs.path(filename)
        
        try:
            # 1. Choose Parser based on extension
            if filename_lower.endswith(('.xlsx', '.xls')):
                exams_data = process_exam_excel(file_path)
                # Excel acts as the "Master" timetable - clear everything first
                Exam.objects.all().delete()
                
            elif filename_lower.endswith('.docx'):
                exams_data = process_nursing_exam_docx(file_path)
                # Word (Nursing) acts as a supplement - DO NOT delete existing exams
                
            else:
                raise Exception("Unsupported file format. Please upload an Excel (.xlsx) or Word (.docx) file.")

            # 2. Process and Save
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
            
            if exam_objects:
                Exam.objects.bulk_create(exam_objects)
                context["success"] = f"Success! Imported {len(exam_objects)} exams."
            else:
                context["info"] = "No valid exam entries found in the file."
                
        except Exception as e:
            context["error"] = f"Error: {str(e)}"
        finally:
            # Ensure cleanup happens even on error
            if fs.exists(filename):
                fs.delete(filename)
                
    return render(request, "upload.html", context)


def public_exam_search(request):
    """
    View function to handle public exam search based on course codes provided as query parameters.
    The view processes the input, constructs a database query to filter exams by course code, and renders the results in a template.
    """
    exams = []
    query = request.GET.get("codes", "")
    if query:
        codes_list = [c.strip().upper() for c in query.split(",")]
        db_query = Q()
        for code in codes_list:
            if code:
                db_query |= Q(course_code__istartswith=code)
        if db_query:
            exams = Exam.objects.filter(db_query).order_by("date")
    return render(request, "exam_search.html", {"exams": exams})


@api_view(["GET"])
@permission_classes([AllowAny])
def check_update(request):
    """API view to check for the latest application update."""
    latest_update = AppUpdate.objects.first()
    if latest_update:
        download_url = request.build_absolute_uri(latest_update.apk_file.url) if not latest_update.apk_file.url.startswith("http") else latest_update.apk_file.url
        return Response({
            "version_code": latest_update.version_code,
            "download_url": download_url,
            "release_notes": latest_update.release_notes,
            "is_mandatory": latest_update.is_mandatory
        })
    return Response({"error": "No updates found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["GET"])
@permission_classes([AllowAny])
def system_status(request):
    """API view to retrieve the general application configuration settings."""
    config, _ = AppConfig.objects.get_or_create(id=1)
    return Response(AppConfigSerializer(config).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def portal_sync_exams(request):
    """API view to sync exams with the university portal for a specific user."""
    import json
    data = json.loads(request.body) if request.body else request.data
    adm, pwd = data.get('admission_number'), data.get('password')

    if not adm or not pwd:
        return Response({"error": "Required fields missing"}, status=status.HTTP_400_BAD_REQUEST)

    codes = scrape_portal(adm, pwd)
    if isinstance(codes, dict) and "error" in codes:
        return Response(codes, status=status.HTTP_400_BAD_REQUEST)

    unit_codes = [c.strip().upper().replace(' ', '') for c in codes]
    matched_exams = Exam.objects.filter(course_code__in=unit_codes)
    serializer = ExamSerializer(matched_exams, many=True)

    return Response({
        "count": len(matched_exams),
        "codes_found": list(set(unit_codes)),
        "exams": serializer.data
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def well_known_assetlinks(request):
    """
    API view to serve the Digital Asset Links JSON file for Android App Links verification.
    """
    assetlinks_data = [
        {
            "relation": [
                "delegate_permission/common.handle_all_urls"
            ],
            "target": {
                "namespace": "android_app",
                "package_name": "com.dita.mobile",
                "sha256_cert_fingerprints": [
                    "40:D7:44:BB:85:70:42:02:B2:84:E8:F6:47:D9:12:05:DA:0D:FB:F1:45:F4:8C:18:7E:DA:3C:BC:D9:17:4C:71"
                ]
            }
        }
    ]
    return Response(assetlinks_data)
