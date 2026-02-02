from .models import SKUMapping
from rest_framework import serializers

class SKUMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SKUMapping
        fields = '__all__'
