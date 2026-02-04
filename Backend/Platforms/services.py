import csv
import re
from io import TextIOWrapper
import pandas as pd
import pdfplumber
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from .models import PurchaseOrder , PurchaseOrderItems
from Mapping.models import SKUMapping

class Utils:
    @staticmethod
    def normalize_status(raw_status: str | None):
        if not raw_status:
            return "CREATED"
        raw = raw_status.strip().upper()
        if raw in ["CONFIRMED", "CREATED"]:
            return "CONFIRMED"
        if raw in ["COMPLETED", "CLOSED", "DONE"]:
            return "COMPLETED"
        if raw in ["EXPIRED"]:
            return "EXPIRED"
        if raw in ["CANCELLED", "CANCELED"]:
            return "CANCELLED"
        return "CREATED"


    @staticmethod
    def parse_date(value):
        if not value or pd.isna(value): # Added check for pandas NaN
            return None
        
        value = str(value).strip()
        formats = [
            "%d %b %Y %I:%M %p",      # Zepto: 15 Dec 2025 12:33 pm
            "%Y-%m-%d %H:%M:%S%z",   # Blinkit
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M",
            "%d-%m-%Y",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt).date()
            except (ValueError, TypeError):
                continue
        return None



class Extractors:
    def csv_extractor(file):
        decoded = TextIOWrapper(file, encoding="utf-8")
        reader = csv.DictReader(decoded)
        return list(reader)
    
    def excel_extractor(file):
        df = pd.read_excel(file)
        return df.to_dict(orient="records")
    
    def pdf_extractor(file):
        text = ""
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        return text
    

class Parsers:
    
    
    # Swiggy Parser 
    def swiggy_parser(rows):
        grouped = defaultdict(list)
        for row in rows:
            grouped[row["PoNumber"]].append(row)
        print("SWIGGY HEADERS:", rows[0].keys())
        pos = []
        for po_no, items in grouped.items():
            first = items[0]
            raw_date = first.get("PoCreatedAt")
            print("RAW PoCreatedAt:", repr(raw_date))
            po_date = Utils.parse_date(raw_date)
            print("PARSED po_date:", po_date)

            po_date = Utils.parse_date(first.get("PoCreatedAt"))
            if not po_date:
                continue  # ⬅️ IMPORTANT

            delivery_date = Utils.parse_date(first.get("ExpectedDeliveryDate"))
            expiry_date = Utils.parse_date(first.get("PoExpiryDate"))

            po = {
                "po_number": po_no,
                "po_date": po_date,
                "delivery_date": delivery_date,
                "expiry_date": expiry_date,
                "status": Utils.normalize_status(first.get("Status")),
                "vendor_name": first["VendorName"],
                "vendor_gstin": None,
                "ship_to_address": first["FacilityName"],
                "bill_to_address": first["Entity"],
                "total_amount": float(first["PoAmount"]),
                "items": [],
            }


            for r in items:
                po["items"].append({
                    "sku_code": str(r["SkuCode"]),
                    "product_name": r["SkuDescription"],
                    "hsn_code": None,
                    "gst_percent": float(r["Tax"]),
                    "quantity": int(r["OrderedQty"]),
                    "mrp": float(r["Mrp"]),
                    "buying_price": float(r["UnitBasedCost"]),
                    "gross_amount": float(r["PoLineValueWithTax"]),
                })

            pos.append(po)

        return pos
    




    # Zepto Parser 
    def zepto_parser(rows):
        grouped = defaultdict(list)

        for row in rows:
            grouped[row["PO No."]].append(row)

        pos = []
        for po_no, items in grouped.items():
            first = items[0]

            po_date = Utils.parse_date(first["PO Date"])
            expiry_date = Utils.parse_date(first["PO Expiry Date"])

            po = {
                "po_number": po_no,
                "po_date": po_date,
                "delivery_date": None,  
                "expiry_date": expiry_date,
                "status": Utils.normalize_status(first["Status"]),
                "vendor_name": first["Vendor Name"],
                "vendor_gstin": None,
                "ship_to_address": first["Del Location"],
                "bill_to_address": first["Vendor Name"],
                "total_amount": float(first["PO Amount"]),
                "items": [],
            }

            for r in items:
                gst = (
                    float(r["CGST %"])
                    + float(r["SGST %"])
                    + float(r["IGST %"])
                )

                po["items"].append({
                    "sku_code": r["SKU"],
                    "product_name": r["SKU Desc"],
                    "hsn_code": str(r["HSN"]),
                    "gst_percent": gst,
                    "quantity": int(r["Qty"]),
                    "mrp": float(r["MRP"]),
                    "buying_price": float(r["Unit Base Cost"]),
                    "gross_amount": float(r["Total Amount"]),
                })

            pos.append(po)

        return pos
    
    
    # Blinkit Parser 
    def blinkit_parser(rows):

        po_groups = defaultdict(list)
        print(po_groups)

        # Group rows by PO number
        for row in rows:
            po_number = str(row.get("po_number")).strip()
            if not po_number:
                continue
            po_groups[po_number].append(row)

        print(po_groups.items())
        normalized_pos = []

        # 2️⃣ Build PO per group
        for po_number, po_rows in po_groups.items():
            first = po_rows[0]

            items = []
            total_amount = Decimal("0.00")

            for r in po_rows:
                line_amount = Decimal(str(r.get("total_amount") or 0))
                total_amount += line_amount

                gst_percent = (
                    Decimal(str(r.get("igst_value") or 0)) +
                    Decimal(str(r.get("cgst_value") or 0)) +
                    Decimal(str(r.get("sgst_value") or 0))
                )

                items.append({
                    "sku_code": str(r.get("item_id")),
                    "product_name": r.get("name"),
                    "hsn_code": None,  # Blinkit doesn’t provide HSN
                    "gst_percent": gst_percent,
                    "quantity": int(float(r.get("units_ordered") or 0)),
                    "mrp": Decimal(str(r.get("mrp") or 0)),
                    "buying_price": Decimal(str(r.get("landing_rate") or 0)),
                    "gross_amount": line_amount,
                })

            po_data = {
                "po_number": po_number,
                "po_date": Utils.parse_date(first.get("order_date")),
                "delivery_date": Utils.parse_date(first.get("appointment_date")),
                "expiry_date": Utils.parse_date(first.get("expiry_date")),
                "status": Utils.normalize_status(first.get("po_state")),
                "vendor_name": (
                    first.get("vendor_name")
                    or first.get("entity_vendor_legal_name")
                ),
                "vendor_gstin": None,
                "ship_to_address": first.get("facility_name"),
                "bill_to_address": first.get("facility_name"),
                "total_amount": total_amount,
                "items": items,
            }

            normalized_pos.append(po_data)

        return normalized_pos

    # Citymall Parser
    def citymall_parsser(text):
        po_number = re.search(r"PO-([0-9]+)", text)
        po_date = re.search(r"Purchase Order Date\s+(\d{2}-\d{2}-\d{4})", text)
        expiry = re.search(r"Expiry Date\s+(\d{2}-\d{2}-\d{4})", text)

        if not po_number:
            return None

        items = []

        item_pattern = re.compile(
            r"\d+\s+([A-Z0-9]+)\s+(.*?)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)",
            re.MULTILINE
        )

        for m in item_pattern.finditer(text):
            items.append({
                "sku_code": m.group(1),
                "product_name": m.group(2).strip(),
                "hsn_code": m.group(3),
                "mrp": Decimal(m.group(4)),
                "buying_price": Decimal(m.group(5)),
                "quantity": int(m.group(6)),
                "gross_amount": Decimal(m.group(8)),
                "gst_percent": Decimal("5.0"),
            })

        return {
            "po_number": po_number.group(1),
            "po_date": datetime.strptime(po_date.group(1), "%d-%m-%Y").date(),
            "delivery_date": None,
            "expiry_date": datetime.strptime(expiry.group(1), "%d-%m-%Y").date(),

            "vendor_name": "JIVO MART PRIVATE LIMITED",
            "vendor_gstin": "07AAFCJ4102J1ZS",

            "ship_to_address": "CityMall Warehouse",
            "bill_to_address": "CityMall",

            "total_amount": sum(i["gross_amount"] for i in items),
            "items": items,
        }

        
        
    # DealShare Parser     
    def dealshare_parser(text):
        po_number_match = re.search(
            r"PO\s*Number.*?\n\s*([0-9]{5,})",
            text,
            re.IGNORECASE | re.DOTALL
        )

        po_date_match = re.search(
            r"PO\s*Created\s*Date.*?\n\s*(\d{2}-\d{2}-\d{4})",
            text,
            re.IGNORECASE | re.DOTALL
        )

        delivery_date_match = re.search(
            r"PO\s*Delivery\s*Date.*?\n\s*(\d{2}-\d{2}-\d{4})",
            text,
            re.IGNORECASE | re.DOTALL
        )

        expiry_date_match = re.search(
            r"PO\s*Expiry\s*Date.*?\n\s*(\d{2}-\d{2}-\d{4})",
            text,
            re.IGNORECASE | re.DOTALL
        )

        total_match = re.search(
            r"Total\s*SKU.*?([\d,]+\.\d{2})",
            text,
            re.IGNORECASE | re.DOTALL
        )

        if not po_number_match:
            return None

        items = []

        sku_line_pattern = re.compile(
            r"^([A-Z0-9]{6,})\s+(.*?)\s+(\d+)\s+0\s+(\d+)\s+(\d+)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})$",
            re.MULTILINE
        )

        for match in sku_line_pattern.finditer(text):
            items.append({
                "sku_code": match.group(1),
                "product_name": match.group(2).strip(),
                "gst_percent": Decimal(match.group(3)),
                "hsn_code": match.group(4),
                "quantity": int(match.group(5)),
                "mrp": Decimal(match.group(6).replace(",", "")),
                "buying_price": Decimal(match.group(7).replace(",", "")),
                "gross_amount": Decimal(match.group(8).replace(",", "")),
            })

        return {
            "po_number": po_number_match.group(1),
            "po_date": datetime.strptime(po_date_match.group(1), "%d-%m-%Y").date()
            if po_date_match else None,
            "delivery_date": datetime.strptime(delivery_date_match.group(1), "%d-%m-%Y").date()
            if delivery_date_match else None,
            "expiry_date": datetime.strptime(expiry_date_match.group(1), "%d-%m-%Y").date()
            if expiry_date_match else None,

            "vendor_name": "SUSTAINQUEST PRIVATE LIMITED",
            "vendor_gstin": "06ABOCS2792M1ZK",
            "ship_to_address": "Chandrawali Hub",
            "bill_to_address": "Merabo Labs Pvt Ltd",

            "total_amount": Decimal(total_match.group(1).replace(",", ""))
            if total_match else Decimal("0.00"),

            "items": items
        }


class Ingestion:
    
    @staticmethod
    @transaction.atomic
    def save_po_bulk(normalized_pos, platform):
        created = 0
        updated = 0

        # 1. Fetch mapping from the Master Sheet structure
        # Using 'external_sku_code' as the lookup key from your SKUMapping model
        mapping_queryset = SKUMapping.objects.filter(platform=platform).values(
            'external_sku_code', 'sap_code', 'sap_name'
        )
        
        # Create a lookup dictionary for O(1) performance
        mappings = {
            m['external_sku_code']: {
                'sku': m['sap_code'], 
                'name': m['sap_name']
            } for m in mapping_queryset
        }

        for data in normalized_pos:
            po, is_created = PurchaseOrder.objects.update_or_create(
                platform=platform,
                po_number=data["po_number"],
                defaults={
                    "po_date": data["po_date"],
                    "delivery_date": data.get("delivery_date"),
                    "expiry_date": data.get("expiry_date"),
                    "vendor_name": data["vendor_name"],
                    "ship_to_address": data["ship_to_address"],
                    "bill_to_address": data["bill_to_address"],
                    "total_amount": data["total_amount"],
                    "status": (data.get("status") or "CREATED").upper(),
                },
            )

            po.items.all().delete()

            item_objects = []
            for item in data["items"]:
                # The raw ID from the vendor file (e.g., Zepto UUID or Swiggy Code)
                vendor_sku_from_file = str(item["sku_code"]).strip()
                vendor_name_from_file = item["product_name"]

                # 2. NORMALIZATION LOGIC
                # Look for the mapping in our Master Sheet data
                mapping_entry = mappings.get(vendor_sku_from_file)
                
                # If found, use your SAP Code/Name. If not, fallback to what's in the file.
                internal_sku = mapping_entry['sku'] if mapping_entry else vendor_sku_from_file
                internal_name = mapping_entry['name'] if mapping_entry else vendor_name_from_file

                item_objects.append(
                    PurchaseOrderItems(
                        purchase_order=po,
                        sku_code=internal_sku,          # Stores SAP Code (e.g. FG0000190)
                        product_name=internal_name,      # Stores SAP Name
                        vendor_sku=vendor_sku_from_file,# Stores Raw ID for reference
                        hsn_code=item.get("hsn_code"),
                        gst_percent=item["gst_percent"],
                        quantity=item["quantity"],
                        mrp=item["mrp"],
                        buying_price=item["buying_price"],
                        gross_amount=item["gross_amount"]
                    )
                )
            
            PurchaseOrderItems.objects.bulk_create(item_objects)

            if is_created:
                created += 1
            else:
                updated += 1

        return created, updated


    @transaction.atomic
    def save_po(data, file, platform):
        po, _ = PurchaseOrder.objects.update_or_create(
            platform=platform,
            po_number=data["po_number"],
            defaults={
                "po_date": data["po_date"],
                "delivery_date": data.get("delivery_date"),
                "expiry_date": data.get("expiry_date"),
                "vendor_name": data["vendor_name"],
                "vendor_gstin": data.get("vendor_gstin"),
                "ship_to_address": data["ship_to_address"],
                "bill_to_address": data["bill_to_address"],
                "total_amount": data["total_amount"],
                "status": (data.get("status") or "CREATED").upper(),
                "raw_file": file,
            },
        )

        po.items.all().delete()

        items = [
            PurchaseOrderItems(purchase_order=po, **item)
            for item in data["items"]
        ]
        PurchaseOrderItems.objects.bulk_create(items)

        return po
