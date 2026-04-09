from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """
    Custom admin interface for the Payment model, allowing administrators to manage payment records with fields for student, amount, phone number, status, timestamp, and M-Pesa receipt.
    The list display includes key payment details, with filters for status and timestamp, and search functionality for student username, phone number, M-Pesa receipt, and external reference.
    """

    list_display = ("student", "amount", "phone_number", "checkout_request_id", "status", "timestamp", "mpesa_receipt")
    list_filter = ("status", "timestamp")
    search_fields = ("student__username", "phone_number", "mpesa_receipt", "external_reference", "checkout_request_id")
