from rest_framework import serializers
from .models import PurchaseOrder , PurchaseOrderItems



class Importserializer(serializers.Serializer):
    PLATFORM_CHOICES = [
        ("dealshare" , "DealShare"),
        ("cityMall" , "CityMall"),
        ("Blinkit" , "Blinkit"),
        ("Swiggy" , "Swiggy"),
        ("Zepto" , "Zepto")
    ]

    file = serializers.FileField()
    platform = serializers.ChoiceField(choices =  PLATFORM_CHOICES)

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    class Meta :
        model = PurchaseOrderItems
        fields = "__all__"


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer
    class Meta:
        model =  PurchaseOrder
        fields = "__all__"