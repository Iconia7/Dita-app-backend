from django.conf import settings
from django.db import models


class Payment(models.Model):
    """
    Model representing a payment made by a student for club dues or event fees.
    It includes fields for the student, amount, phone number, MPESA receipt, external reference, status, and timestamp.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    phone_number = models.CharField(max_length=15)
    mpesa_receipt = models.CharField(max_length=50, null=True, blank=True, unique=True)
    external_reference = models.CharField(max_length=100, unique=True)
    checkout_request_id = models.CharField(max_length=100, null=True, blank=True, unique=True)
    merchant_request_id = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.status}"
