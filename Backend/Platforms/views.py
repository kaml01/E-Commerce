from django.shortcuts import render
from rest_framework import viewsets
from rest_framework .decorators import action
from rest_framework.parsers import MultiPartParser , FormParser
from rest_framework import status
from rest_framework.response import Response

from .models import PurchaseOrder , PurchaseOrderItems
from  .serializers import  PurchaseOrderItemSerializer , PurchaseOrderSerializer , Importserializer
from .services import Ingestion , Parsers , Extractors

class PurchaseOrderView(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser], url_path='upload_po')
    def upload_po(self, request):
        serializer = Importserializer(data=request.data)

        if serializer.is_valid():
            file = serializer.validated_data['file']
            platform = serializer.validated_data['platform'].strip().lower()


            # Extract rows based on File type 
            if file.name.endswith((".csv")):
                rows = Extractors.csv_extractor(file)
            elif file.name.endswith((".pdf")):
                rows = Extractors.pdf_extractor(file)
            elif file.name.endswith((".xls", ".xlsx")): 
                rows = Extractors.excel_extractor(file)
            else :
                return Response(
                    {"message": "File FOrmat not supported (Supported Formats : xls , csv, pdf )"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )                

            # Normalize POs based on Platforms 
            if platform == 'swiggy':
                normalized_pos = Parsers.swiggy_parser(rows)
            elif platform == 'zepto':
                normalized_pos = Parsers.zepto_parser(rows)
                print(normalized_pos)
            elif platform == 'blinkit':
                normalized_pos = Parsers.blinkit_parser(rows)
            else :
                return Response(
                    {"message": "Platform not supported"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )  

            # Ingesting normalized POS into the model / Database
            created_count, updated_count = Ingestion.save_po_bulk(normalized_pos, platform)
            return Response({
                "message": f"Successfully processed {platform} file.",
                "created": created_count,
                "updated": updated_count
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

