from django.db import models

# Create your models here.
class PurchaseOrderHeaders(models.Model):
    po_number = models.CharField(max_length=50, primary_key=True)
    vendor_code = models.CharField(max_length=50)
    order_date = models.DateField(null=True)
    expiry_date = models.DateField(null=True) 
    overall_status = models.CharField(max_length=100)

    def __str__(self):
        return self.po_number

class SKUMapping(models.Model):
    external_sku_code = models.CharField(max_length=100 , unique=True , db_index=True)
    sap_code = models.CharField(max_length=100)
    sap_name = models.CharField(max_length=255)
    category = models.CharField(max_length=50)
    sub_category = models.CharField(max_length=50)
    case_pack = models.DecimalField(max_digits=5 , decimal_places=2)
    uom = models.CharField(max_length=10)

    def __str__(self):
        return -f"{self.external_sku_code}  -> {self.sap_code}"



class PurchaseOrderLines(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrderHeaders, on_delete=models.CASCADE, related_name='items')
    external_id = models.CharField(max_length=100) # External ID from Amazon
    asin = models.CharField(max_length=100)
    sap_code = models.CharField(max_length=100)
    sap_name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    uom = models.CharField(max_length=20)
    requested_qty = models.FloatField(default=0)
    accepted_qty = models.FloatField(default=0)
    received_qty = models.FloatField(default=0)
    cancelled_qty = models.FloatField(default=0)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_requested_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_accepted_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_received_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_cancelled_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fulfillment_center = models.CharField(max_length=100) 
    availability_status = models.CharField(max_length=100) 
    item_status = models.CharField(max_length=50) 
