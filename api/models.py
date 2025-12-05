from django.conf import settings
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    fcm_token = models.CharField(max_length=255, blank=True, null=True)
    points = models.IntegerField(default=0)
    # ... existing fields ...
    admission_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    program = models.CharField(max_length=100, null=True, blank=True)
    year_of_study = models.IntegerField(default=1)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    
    # CHANGE: Replace the boolean with a Date
    # We keep 'is_paid_member' but we won't set it manually anymore.
    # We will calculate it based on this date.
    membership_expiry = models.DateTimeField(null=True, blank=True) 
    
    @property
    def attendance_percentage(self):
        # 1. Count total events (You might want to filter by date < now in future)
        # We import Event inside to avoid circular import errors
        from .models import Event 
        total_events = Event.objects.count()
        
        if total_events == 0:
            return 0
            
        # 2. Count how many this user attended
        # 'attended_events' is the related_name we set in the Event model
        attended_count = self.attended_events.count() 
        
        # 3. Calculate Percentage
        return int((attended_count / total_events) * 100)

    @property
    def is_active_member(self):
        """
        Calculates status dynamically. 
        Returns True if expiry date is in the future.
        """
        if self.membership_expiry and self.membership_expiry > timezone.now():
            return True
        return False

class Task(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    due_date = models.DateTimeField()
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.user.username}" 
    
class Exam(models.Model):
    # REMOVED unique=True so we can have multiple venues for the same exam
    course_code = models.CharField(max_length=50) 
    title = models.CharField(max_length=200, blank=True, null=True)
    
    # Combined Date + Start Time (What Flutter Expects)
    date = models.DateTimeField() 
    
    # We can keep end_time separate for reference, Flutter will just ignore it if it doesn't need it
    end_time = models.TimeField(null=True, blank=True)
    
    venue = models.CharField(max_length=100)
    duration_hours = models.DecimalField(max_digits=4, decimal_places=2, default=2.0)

    def __str__(self):
        # Using the format you prefer
        return f"{self.course_code} - {self.date.strftime('%d %b %H:%M')}"      

class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateTimeField()
    venue = models.CharField(max_length=100)
    # This image will go to Cloudinary automatically
    image = models.ImageField(upload_to='events/', null=True, blank=True) 
    checked_in_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name='attended_events', # Gives reverse access via user.attended_events
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
class AppUpdate(models.Model):
    version_code = models.IntegerField(help_text="Must match build.gradle version code") # e.g. 5
    version_name = models.CharField(max_length=20) # e.g. "1.0.5"
    apk_file = models.FileField(upload_to='updates/') # Goes to Cloudinary
    is_mandatory = models.BooleanField(default=False) # Force update?
    release_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at'] # Newest first

    def __str__(self):
        return f"v{self.version_name} ({self.version_code})"    

class RSVP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'event')
    
class Resource(models.Model):
    TYPE_CHOICES = [
        ('PDF', 'PDF Document'),
        ('PPT', 'Presentation (PPT/Slides)'),
        ('DOC', 'Word Document'),       # New
        ('XLS', 'Excel Spreadsheet'),   # New
        ('IMG', 'Image'),               # New
        ('ZIP', 'Zip Archive'),         # New
        ('LINK', 'External Link'),
    ]
    title = models.CharField(max_length=200)
    resource_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    link = models.URLField(help_text="Link to Google Drive or Website", blank=True, null=True)
    file = models.FileField(upload_to='resources/', blank=True, null=True)
    description = models.CharField(max_length=255, blank=True)
    
    def __str__(self):
        return self.title 
    
class PasswordResetOTP(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        # Valid for 10 minutes
        return self.created_at >= timezone.now() - timezone.timedelta(minutes=10)     

class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    phone_number = models.CharField(max_length=15)
    
    # The M-Pesa Receipt (e.g., QGH5...) - Nullable until payment completes
    mpesa_receipt = models.CharField(max_length=50, null=True, blank=True, unique=True)
    
    # The Linker: specific ID we send to PayHero to track this request
    external_reference = models.CharField(max_length=100, unique=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.status}"
    
class Announcement(models.Model):
    title = models.CharField(max_length=200)
    message = models.TextField()
    date_posted = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title    