from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.core.files.storage import FileSystemStorage
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly

from config.utils import process_exam_excel
from apps.users.models import User

from .models import Exam, Resource, Task
from .serializers import ExamSerializer, ResourceSerializer, TaskSerializer


class ExamViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for listing and retrieving exams, with support for filtering by course codes provided as query parameters."""
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer
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
    View function to handle the upload of an Excel file containing exam timetable data.
    The view processes the uploaded file, extracts exam information, and updates the Exam model in the database accordingly.
    It also provides feedback on the success or failure of the import process through the rendered template.
    """
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
