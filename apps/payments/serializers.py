from rest_framework import serializers
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for the Payment model, including all fields."""

    class Meta:
        model = Payment
        fields = "__all__"
