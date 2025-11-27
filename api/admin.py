from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Event, Payment

# 1. Custom User Admin
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'admission_number', 'program', 'year_of_study', 'is_paid_member')
    list_filter = ('is_paid_member', 'program', 'year_of_study', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Student Details', {'fields': ('admission_number', 'program', 'year_of_study', 'phone_number', 'is_paid_member')}),
    )

# 2. Event Admin
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'venue')
    list_filter = ('date',)

# 3. Payment Admin (UPDATED)
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    # We changed 'is_verified' to 'status' to match your PayHero logic
    list_display = ('student', 'amount', 'phone_number', 'status', 'timestamp', 'mpesa_receipt')
    list_filter = ('status', 'timestamp')
    search_fields = ('student__username', 'phone_number', 'mpesa_receipt', 'external_reference')