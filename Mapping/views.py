from django.shortcuts import render
from .models import SKUMapping
from .serializers import SKUMappingSerializer
from rest_framework.response import Response
from .service import MappingService
from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser , FormParser
from rest_framework.decorators import action
from rest_framework import status


class SKUMappingView(viewsets.ModelViewSet):
    queryset = SKUMapping.objects.all()
    serializer_class = SKUMappingSerializer

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser], url_path='upload_mapping')
    def upload_mapping(self, request):
        uploaded_file = request.FILES.get('file')
        
        if not uploaded_file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            processed_lines = MappingService.sync_mappings(uploaded_file)
            return Response({
                "message": "Bulk mapping synced successfully",
                "records_updated": processed_lines
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)