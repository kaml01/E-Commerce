from django.db import models

class SKUMapping(models.Model):
    PLATFORM_CHOICES = [
        ("dealshare", "DealShare"),
        ("citymall", "CityMall"),
        ("blinkit", "Blinkit"),
        ("swiggy", "Swiggy"),
        ("zepto", "Zepto")
    ]
    platform = models.CharField(
        max_length=20, 
        choices=PLATFORM_CHOICES, 
        default="zepto", 
        db_index=True
    )
    external_sku_code = models.CharField(max_length=100, db_index=True)
    sap_code = models.CharField(max_length=100)
    sap_name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, null=True, blank=True)
    sub_category = models.CharField(max_length=50, null=True, blank=True)
    case_pack = models.DecimalField(max_digits=10, decimal_places=2, default=1.0)
    uom = models.CharField(max_length=10, default="PCS")
    class Meta:
        unique_together = ('platform', 'external_sku_code')
    def __str__(self):
        return f"[{self.platform}] {self.external_sku_code} -> {self.sap_code}"