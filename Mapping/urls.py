from .models import SKUMapping
from . import views
from django.urls import path , include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register("" , views.SKUMappingView , basename="sku_mapping")

urlpatterns = [
    path('' , include(router.urls))
]