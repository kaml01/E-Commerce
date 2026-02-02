from .models import SKUMapping
from decimal import Decimal
from django.db import transaction
import pandas as pd

class MappingService:
    @staticmethod
    def sync_mappings(file_obj):
        if file_obj.name.endswith('.xlsx') or file_obj.name.endswith('.xls'):
            df = pd.read_excel(file_obj)
        else:
            df = pd.read_csv(file_obj)

        sync_count = 0

        with transaction.atomic():
            for _, row in df.iterrows():
                raw_platform = str(row.get('FORMAT', '')).strip().lower()
                normalized_platform = raw_platform.replace(" ", "")
                external_id = str(row.get('FORMAT SKU Code', '')).strip()
                if not external_id or external_id.lower() == 'nan' or not normalized_platform:
                    continue
                SKUMapping.objects.update_or_create(
                    platform=normalized_platform,
                    external_sku_code=external_id,
                    defaults={
                        'sap_code': str(row.get('SKU SAP Code', 'NA')).strip() if pd.notna(row.get('SKU SAP Code')) else 'NA',
                        'sap_name': str(row.get('SKU SAP NAME', 'NA')).strip() if pd.notna(row.get('SKU SAP NAME')) else 'NA',
                        'category': row.get('Category') if pd.notna(row.get('Category')) else 'NA',
                        'sub_category': row.get('Sub Category') if pd.notna(row.get('Sub Category')) else None,
                        'uom': row.get('UOM') if pd.notna(row.get('UOM')) else 'PCS',
                        'case_pack': Decimal(str(row.get('Case Pack', '1.00'))) if pd.notna(row.get('Case Pack')) else Decimal('1.00')
                    }
                )
                sync_count += 1
                
        return sync_count
    