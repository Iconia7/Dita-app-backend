from rest_framework import serializers
from .models import User, Event, Payment

class UserSerializer(serializers.ModelSerializer):
    # 1. We force this field to be calculated by a function below
    is_paid_member = serializers.SerializerMethodField()
    
    # 2. We allow the expiry date to be read
    membership_expiry = serializers.DateTimeField(format="%Y-%m-%d", read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 
            'username', 
            'email', 
            'admission_number', 
            'program', 
            'year_of_study', 
            'phone_number',
            'is_paid_member', # Ensure this is in the list
            'membership_expiry',
            'qr_code_data'
        ]
        
    qr_code_data = serializers.SerializerMethodField()

    def get_qr_code_data(self, obj):
        return obj.admission_number

    # 3. This function runs every time data is requested
    def get_is_paid_member(self, obj):
        # We explicitly call the model property here
        return obj.is_active_member
    
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