from rest_framework import serializers
from .models import User, Event, Payment

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # We only send these fields to the mobile app
        fields = ['id', 'username', 'email', 'admission_number', 'program', 'year_of_study', 'is_paid_member', 'qr_code_data']
        
    # We add a custom field for the QR code data string
    qr_code_data = serializers.SerializerMethodField()

    def get_qr_code_data(self, obj):
        # The QR code will just be the Admission Number (simple version)
        return obj.admission_number
    
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'email', 'admission_number', 'phone_number', 'program', 'year_of_study']

    def create(self, validated_data):
        # We use create_user to automatically hash the password
        user = User.objects.create_user(
            username=validated_data['username'], # Usually Admission No
            password=validated_data['password'],
            email=validated_data.get('email', ''),
            admission_number=validated_data.get('admission_number', ''),
            phone_number=validated_data.get('phone_number', ''),
            program=validated_data.get('program', ''),
            year_of_study=validated_data.get('year_of_study', 1)
        )
        return user    

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'