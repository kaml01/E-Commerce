import pandas as pd
import numpy as np
from django.db import transaction
from .models import PurchaseOrderHeaders, PurchaseOrderLines, SKUMapping
from datetime import datetime, timedelta , date

class utils:
    def calculate_item_status(row):
        d = str(row.get('Status', '')).strip()
        e = str(row.get('Availability', '')).strip()
        i = float(row.get('Requested quantity', 0) or 0)
        j = float(row.get('Accepted quantity', 0) or 0)
        k = float(row.get('Received quantity', 0) or 0)
        l = float(row.get('Cancelled quantity', 0) or 0)
        # Date logic for "EXPIRED"
        order_date = row.get('Order date') 
        # Note: parse_excel_date helper should be used here to ensure order_date is a python date object
        is_past = order_date < date.today() if order_date else False

        # 1. EXPIRED Checks
        if e == "AC - Accepted: In stock" and is_past:
            if d == "Unconfirmed" and j == 0 and k == 0 and l == 0:
                return "EXPIRED"
            if d == "Confirmed" and j > 0 and k == 0 and l == 0:
                return "EXPIRED"
            if d == "Confirmed" and i > 0 and j == 0 and k == 0 and l == 0:
                return "EXPIRED"

        # 2. MOV & CANCELLED Checks
        if d == "Confirmed" and e == "OS - Cancelled: Out of stock" and j == 0 and k == 0 and l == 0:
            return "MOV"

        if d == "Closed":
            if e == "OS - Cancelled: Out of stock" and j == 0 and k == 0 and l == 0:
                return "CANCELLED"
            if e == "AC - Accepted: In stock":
                if j == 0 and k == 0 and l > 0: return "CANCELLED"
                if j > 0 and k == 0 and l > 0: return "CANCELLED"

        # 3. COMPLETED Checks
        if e == "AC - Accepted: In stock":
            if d == "Confirmed" and j > 0 and k > 0:
                return "COMPLETED"
            if d == "Closed":
                if j > 0 and k > 0: return "COMPLETED" # Covers J>0,K>0,L=0 and J>0,K>0,L>0
                if j == 0 and k > 0 and l > 0: return "COMPLETED"

        # 4. PENDING Checks
        if e == "AC - Accepted: In stock":
            if d == "Unconfirmed" and j == 0 and k == 0 and l == 0:
                return "PENDING"
            if d == "Confirmed":
                if j > 0 and k == 0 and l == 0: return "PENDING"
                if i > 0 and j == 0 and k == 0 and l == 0: return "PENDING"

        return ""


    def calculate_overall_supply_status(item_status, received_qty, requested_qty):
        if item_status == "COMPLETED":
            if received_qty < requested_qty:
                return "SHORT SUPPLIED"
            elif received_qty >= requested_qty:
                return "FULL SUPPLIED"
        return ""




class MappingService:
    @staticmethod
    def sync_mappings(file_obj):
        df = pd.read_excel(file_obj) if file_obj.name.endswith('.xlsx') else pd.read_csv(file_obj)

        sync_count = 0
        with transaction.atomic():
            for _, row in df.iterrows():
                asin = str(row.get('FORMAT SKU Code', '')).strip()
                if not asin or asin.lower() == 'nan':
                    continue

                SKUMapping.objects.update_or_create(
                    external_sku_code=asin,
                    defaults={
                        'sap_code': row.get('SKU SAP Code') if pd.notna(row.get('SKU SAP Code')) else 'NA',
                        'sap_name': row.get('SKU SAP NAME') if pd.notna(row.get('SKU SAP NAME')) else 'NA',
                        'category': row.get('Category') if pd.notna(row.get('Category')) else 'NA',
                        'sub_category': row.get('Sub Category') if pd.notna(row.get('Sub Category')) else None,
                        'uom': row.get('UOM') if pd.notna(row.get('UOM')) else 'NA',
                        'case_pack' : row.get('Case Pack') if pd.notna(row.get('Case Pack')) else '0.00'
                    }
                )
                sync_count += 1
        return sync_count
    

class PurchaseServices:
    @staticmethod
    def parse_amazon_date(value):
        """Safely converts Amazon/Excel serial dates and strings."""
        if pd.isna(value) or value == '':
            return None
        try:
            # Handle numeric Excel dates (46048.0)
            return (datetime(1899, 12, 30) + timedelta(days=float(value))).date()
        except (ValueError, TypeError):
            try:
                # Handle standard string dates (YYYY-MM-DD or DD/MM/YYYY)
                return pd.to_datetime(value).date()
            except:
                return None

    @staticmethod
    def process_po_file(file_obj, mapping_dict):
        if file_obj.name.endswith('.xlsx') or file_obj.name.endswith('.xls'):
            df = pd.read_excel(file_obj)
        else:
            try:
                df = pd.read_csv(file_obj)
            except UnicodeDecodeError:
                file_obj.seek(0) 
                df = pd.read_csv(file_obj, encoding='latin-1')
        
        df['Order date'] = df['Order date'].apply(PurchaseServices.parse_amazon_date)

        processed_count = 0
        with transaction.atomic():
            for po_num, items in df.groupby('PO'):
                line_item_objects = []
                first_row = items.iloc[0]
                
                # Create the Header first
                po_header, _ = PurchaseOrderHeaders.objects.update_or_create(
                    po_number=str(po_num),
                    defaults={
                        'vendor_code': first_row.get('Vendor code', 'NA'),
                        'order_date': first_row.get('Order date'),
                        'expiry_date': PurchaseServices.parse_amazon_date(first_row.get('Window end')),
                        'overall_status': "Processed"
                    }
                )

                # 3. Process each line
                for _, row in items.iterrows():
                    # Calculate statuses using your utils class
                    i_status = utils.calculate_item_status(row)
                    
                    # Lookup mapping info
                    asin = str(row.get('ASIN', '')).strip()
                    map_info = mapping_dict.get(asin)

                    line_item_objects.append(PurchaseOrderLines(
                        purchase_order=po_header,
                        external_id=row.get('External ID', 'NA'),
                        asin=asin,
                        
                        # Enrichment from Mapping Table
                        sap_code=getattr(map_info, 'sap_code', 'NOT_MAPPED'),
                        sap_name=getattr(map_info, 'sap_name', row.get('SKU Name', 'NA')),
                        category=getattr(map_info, 'category', 'NA'),
                        uom=getattr(map_info, 'uom', 'PCS'),

                        # Quantities
                        requested_qty=row.get('Requested quantity', 0),
                        accepted_qty=row.get('Accepted quantity', 0),
                        received_qty=row.get('Received quantity', 0),
                        cancelled_qty=row.get('Cancelled quantity', 0),

                        # Costs
                        unit_cost=row.get('Cost price', 0),
                        total_requested_cost=row.get('Total requested cost', 0),
                        total_accepted_cost=row.get('Total accepted cost', 0),
                        total_received_cost=row.get('Total received cost', 0),
                        total_cancelled_cost=row.get('Total cancelled cost', 0),

                        # Fulfillment & Status
                        fulfillment_center=row.get('Ship-to location', 'NA'),
                        availability_status=row.get('Availability', 'NA'),
                        item_status=i_status
                    ))

                # 4. Clean up old lines and Bulk Create new ones
                PurchaseOrderLines.objects.filter(purchase_order=po_header).delete()
                PurchaseOrderLines.objects.bulk_create(line_item_objects)
                processed_count += 1

        return processed_count