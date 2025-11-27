from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    # Student Details
    admission_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    program = models.CharField(max_length=100, null=True, blank=True)
    year_of_study = models.IntegerField(default=1)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    
    # Roles & Status
    is_dita_official = models.BooleanField(default=False)
    is_paid_member = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.username} - {self.admission_number}"

class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateTimeField()
    venue = models.CharField(max_length=100)
    attendees = models.ManyToManyField(User, related_name='events_attending', blank=True)
    checked_in_users = models.ManyToManyField(User, related_name='events_checked_in', blank=True)

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