from rest_framework import serializers
from .models import Exam, Resource, Task, User, Event, Payment, Announcement

class UserSerializer(serializers.ModelSerializer):
    # 1. Custom Calculated Fields
    is_paid_member = serializers.SerializerMethodField()
    qr_code_data = serializers.SerializerMethodField()
    
    # 2. formatting the date
    membership_expiry = serializers.DateTimeField(format="%Y-%m-%d", read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 
            'username', 
            'email', 
            'admission_number', 
            'program',
            'avatar', 
            'year_of_study', 
            'phone_number',
            'is_paid_member', 
            'membership_expiry',
            'points',            # Ensure points is here
            'attendance_percentage',
            'fcm_token',    # <--- Needed for Notifications
            'qr_code_data'  # <--- THIS WAS MISSING, CAUSING THE ERROR
        ]

    def get_qr_code_data(self, obj):
        # We return the admission number to be generated into a QR code
        return obj.admission_number

    def get_is_paid_member(self, obj):
        # Runs the logic in models.py (checking the date)
        return obj.is_active_member
    
class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ['user', 'created_at']
        
class ExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = '__all__'        
                    

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'email', 'admission_number', 'phone_number', 'program', 'year_of_study']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data.get('email', ''),
            admission_number=validated_data.get('admission_number', ''),
            phone_number=validated_data.get('phone_number', ''),
            program=validated_data.get('program', ''),
            year_of_study=validated_data.get('year_of_study', 1)
        )
        return user

class EventSerializer(serializers.ModelSerializer):
    # Add a field to check if the CURRENT user asking for events has RSVP'd
    has_rsvped = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ['id', 'title', 'description', 'date', 'venue', 'image', 'has_rsvped']

    def get_has_rsvped(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.rsvp_set.filter(user=request.user).exists()
        return False
    
class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = '__all__'        

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'

class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = '__all__'