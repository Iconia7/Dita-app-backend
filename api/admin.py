from import_export import resources  # <--- THIS IS THE CORRECT ONE
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from import_export.admin import ImportExportModelAdmin
from django.utils.html import format_html
import qrcode
import base64
from io import BytesIO
from .models import RSVP, Exam, Task, User, Event, Payment, Announcement, Resource # <--- Added Resource here

admin.site.register(RSVP)

class ExamResource(resources.ModelResource):
    class Meta:
        model = Exam
        import_id_fields = ('course_code',) # Use course code to update existing rows
        fields = ('course_code', 'title', 'date', 'venue', 'duration_hours')

@admin.register(Exam)
class ExamAdmin(ImportExportModelAdmin):
    resource_class = ExamResource
    list_display = ('course_code', 'title', 'date', 'venue')
    search_fields = ('course_code', 'title')

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'due_date', 'is_completed', 'created_at')
    list_filter = ('is_completed', 'due_date')
    search_fields = ('title', 'user__username')
# 1. Custom User Admin
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'admission_number', 'program', 'is_active_member', 'membership_expiry', 'points', 'fcm_token')
    list_filter = ('membership_expiry', 'program', 'year_of_study', 'is_staff')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Student Details', {'fields': ('admission_number', 'program', 'year_of_study', 'phone_number', 'membership_expiry', 'points', 'fcm_token')}),
    )

# 2. Event Admin
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'venue', 'qr_code_preview')
    readonly_fields = ('qr_code_preview',)

    def qr_code_preview(self, obj):
        if not obj.pk:
            return "Save the event first to generate QR"
            
        # 1. Generate QR based on the Event ID
        qr = qrcode.QRCode(version=1, box_size=5, border=2)
        qr.add_data(str(obj.id)) # <--- This is the data the App scans
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # 2. Convert to Base64 to display in HTML
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode()

        # 3. Return HTML Image tag
        return format_html(f'<img src="data:image/png;base64,{img_str}" width="150" height="150" />')

    qr_code_preview.short_description = "Scan for Attendance"

# 3. Payment Admin
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('student', 'amount', 'phone_number', 'status', 'timestamp', 'mpesa_receipt')
    list_filter = ('status', 'timestamp')
    search_fields = ('student__username', 'phone_number', 'mpesa_receipt', 'external_reference')

# 4. Announcement Admin
@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'date_posted', 'is_active')
    list_filter = ('is_active', 'date_posted')
    search_fields = ('title', 'message')

# 5. Resource Admin (NEW)
@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'resource_type', 'link')
    list_filter = ('resource_type',)
    search_fields = ('title', 'description')