from django.shortcuts import render
from rest_framework .decorators import action
from rest_framework import viewsets
from rest_framework.views import APIView 
from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser , FormParser
from rest_framework import status
from rest_framework.response import Response

from .models import  PurchaseOrderHeaders  , PurchaseOrderLines , SKUMapping
from .serializers import Importserializer  , PurchaseOrderSerializer , SKUMappingSerializer , PurchaseOrderLinesSerializer
from .services import MappingService, PurchaseServices, utils # Add PurchaseServices and utils

# Purchase order View 
class PurchaseOrderViewset(viewsets.ModelViewSet):
    queryset = PurchaseOrderHeaders.objects.all()
    serializer_class = PurchaseOrderSerializer

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser], url_path='upload_po')
    def upload_po(self, request):
        serializer = Importserializer(data=request.data)

        if serializer.is_valid():
            uploadedFile = serializer.validated_data['file']
            
            # 1. Pre-fetch mappings into a dictionary for O(1) lookup speed
            # This is the 'mapping_dict' parameter the service needs
            mapping_dict = {m.external_sku_code: m for m in SKUMapping.objects.all()}
            
            try:
                # 2. Call the Normalizer Service
                processed_count = PurchaseServices.process_po_file(uploadedFile, mapping_dict)
                
                return Response({
                    "message": "File processed and normalized successfully",
                    "filename": uploadedFile.name,
                    "pos_processed": processed_count
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                # Catch errors like missing columns or file corruption
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class PurchaseOrderLinesView(viewsets.ModelViewSet):
    queryset = PurchaseOrderLines.objects.all()
    serializer_class = PurchaseOrderLinesSerializer


# SKU MApping Views
class SKUMappingView(viewsets.ModelViewSet):
    queryset = SKUMapping.objects.all()
    serializer_class = SKUMappingSerializer

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser], url_path='upload_mapping')
    def upload_mapping(self, request):
        serializer = Importserializer(data=request.data)

        if serializer.is_valid():
            uploadedFile = serializer.validated_data['file']
            try:
                processed_lines = MappingService.sync_mappings(uploadedFile)
                return Response({
                    "message": "Mapping synced successfully",
                    "records_updated": processed_lines
                }, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)