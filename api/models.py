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

class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateTimeField()
    venue = models.CharField(max_length=100)
    image = models.ImageField(upload_to='events/', blank=True, null=True) 
    
    # Logic
    attendees = models.ManyToManyField(User, related_name='rsvped_events', blank=True)
    checked_in_users = models.ManyToManyField(User, related_name='attended_events', blank=True)

    def __str__(self):
        return self.title
    
class Resource(models.Model):
    TYPE_CHOICES = [
        ('PDF', 'PDF Document'),
        ('PPT', 'Presentation'),
        ('LINK', 'External Link'),
    ]
    title = models.CharField(max_length=200)
    resource_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    link = models.URLField(help_text="Link to Google Drive or Website")
    description = models.CharField(max_length=255, blank=True)
    
    def __str__(self):
        return self.title    

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