from django.shortcuts import render
from rest_framework .decorators import action
from rest_framework import viewsets
from rest_framework.views import APIView 
from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser , FormParser
from rest_framework import status
from rest_framework.response import Response

from .models import  PurchaseOrderHeaders  , PurchaseOrderLines 
from .serializers import Importserializer  , PurchaseOrderSerializer , PurchaseOrderLinesSerializer
from .services import  PurchaseServices, utils # Add PurchaseServices and utils
from Mapping.models import SKUMapping

# Purchase order View 
class PurchaseOrderViewset(viewsets.ModelViewSet):
    queryset = PurchaseOrderHeaders.objects.all()
    serializer_class = PurchaseOrderSerializer

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser], url_path='upload_po')
    def upload_po(self, request):
        serializer = Importserializer(data=request.data)

        if serializer.is_valid():
            uploadedFile = serializer.validated_data['file']
            mapping_dict = {m.external_sku_code: m for m in SKUMapping.objects.all()}
            
            try:
                processed_count = PurchaseServices.process_po_file(uploadedFile, mapping_dict)
                
                return Response({
                    "message": "File processed and normalized successfully",
                    "filename": uploadedFile.name,
                    "pos_processed": processed_count
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PurchaseOrderLinesView(viewsets.ModelViewSet):
    queryset = PurchaseOrderLines.objects.all()
    serializer_class = PurchaseOrderLinesSerializer


