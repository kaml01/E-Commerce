from rest_framework import serializers
from .models import PurchaseOrderHeaders , PurchaseOrderLines

class Importserializer(serializers.Serializer):
    file = serializers.FileField()



class PurchaseOrderLinesSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderLines
        fields = '__all__'


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderLinesSerializer(many = True)
    class Meta:
        model = PurchaseOrderHeaders
        fields = '__all__'