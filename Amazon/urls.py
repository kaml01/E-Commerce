from django.urls import path,include
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('amazon_po' , views.PurchaseOrderViewset , basename='amazon_po')
router.register('sku_mapping' , views.SKUMappingView , basename='sku_mapping')
router.register('amazon_po_lines' , views.PurchaseOrderLinesView , basename='amazon_po_lines')

urlpatterns = [
    path('' , include(router.urls)),
    # path('', PurchaseOrderImportView.as_view(), name='import-po'),
]