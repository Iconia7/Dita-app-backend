from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Event, Payment

# 1. Custom User Admin
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # SHOW the calculated property 'is_active_member' and the date 'membership_expiry'
    list_display = ('username', 'admission_number', 'program', 'year_of_study', 'is_active_member', 'membership_expiry')
    
    # FILTER by the date field (Properties cannot be used in filters directly)
    list_filter = ('membership_expiry', 'program', 'year_of_study', 'is_staff')
    
    # Allow editing the Expiry Date manually
    fieldsets = UserAdmin.fieldsets + (
        ('Student Details', {'fields': ('admission_number', 'program', 'year_of_study', 'phone_number', 'membership_expiry')}),
    )

# 2. Event Admin
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'venue')
    list_filter = ('date',)

# 3. Payment Admin
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('student', 'amount', 'phone_number', 'status', 'timestamp', 'mpesa_receipt')
    list_filter = ('status', 'timestamp')
    search_fields = ('student__username', 'phone_number', 'mpesa_receipt', 'external_reference')