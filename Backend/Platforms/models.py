from django.db import models

# PO Headers
class PurchaseOrder(models.Model):
    PLATFORM_CHOICES = [
        ("dealshare" , "DealShare"),
        ("cityMall" , "CityMall"),
        ("Blinkit" , "Blinkit"),
        ("Swiggy" , "Swiggy"),
        ("Zepto" , "Zepto")
    ]

    STATUS_CHOICES = [
        ("CREATED", "Created"),
        ("CONFIRMED", "Confirmed"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
        ("EXPIRED", "Expired"),
    ]
    platform = models.CharField(max_length=20 , choices=PLATFORM_CHOICES)
    po_number = models.CharField(max_length=100)
    po_date = models.DateField()
    delivery_date = models.DateField(null=True , blank=True)
    expiry_date = models.DateField(null=True , blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="CREATED"
    )
    vendor_name = models.CharField(max_length=255)
    vendor_gstin = models.CharField(max_length=20, null=True,blank=True)

    ship_to_address = models.TextField()
    bill_to_address = models.TextField()

    total_amount = models.DecimalField(max_digits=12 , decimal_places=2)
    raw_file = models.FileField(
        upload_to="po_raw/",
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("platform" , "po_number")
    
    def __str__(self):
        return f"{self.platform} - {self.po_number}"

        
class PurchaseOrderItems(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder , on_delete=models.CASCADE , related_name="items")
    sku_code = models.CharField(max_length=100)  
    vendor_sku = models.CharField(max_length=100  , blank=True)
    product_name = models.CharField(max_length=255)
    hsn_code = models.CharField(max_length=20, null=True,blank=True)
    gst_percent = models.DecimalField(max_digits=12 ,decimal_places=2)
    quantity = models.IntegerField()
    mrp = models.DecimalField(max_digits=10 , decimal_places=2)
    buying_price = models.DecimalField(max_digits=10 , decimal_places=2)
    gross_amount = models.DecimalField(max_digits=12 , decimal_places=2)

