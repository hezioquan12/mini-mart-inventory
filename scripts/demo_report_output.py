from pathlib import Path
from decimal import Decimal
import json

from src.inventory.product_manager import ProductManager
from src.sales.transaction import Transaction
from src.report_and_sreach import report
from datetime import datetime

# prepare product manager
pm = ProductManager(storage_file=Path('data_demo_products.json'))
pm.products = []
pm.category_mgr._names = ['Drinks','Household','Misc']
pm.category_mgr._rebuild_normalized_cache()

# add products
pm.add_product('P1','Milk','Drinks',10000,15000,50,5,'box')
pm.add_product('P2','Soap','Household',2000,3000,100,10,'piece')
pm.add_product('P3','Candy','Misc',500,1000,200,20,'pack')

# dummy transaction manager
class DummyTM:
    def __init__(self, transactions=None):
        self.transactions = transactions or []
    def list_transactions(self):
        return list(self.transactions)

# create some transactions
now = datetime.now()
transactions = [
    Transaction(transaction_id='T1', product_id='P1', trans_type='EXPORT', quantity=10, date=now),
    Transaction(transaction_id='T2', product_id='P2', trans_type='EXPORT', quantity=2, date=now),
    Transaction(transaction_id='T3', product_id='P1', trans_type='IMPORT', quantity=5, date=now),
    Transaction(transaction_id='T4', product_id='P999', trans_type='EXPORT', quantity=3, date=now),
]

tm = DummyTM(transactions)

# compute summary
summary = report.compute_financial_summary(pm, tm, top_k=5, include_zero_sales=True, currency='VND')

# print raw JSON-friendly summary
print('--- RAW SUMMARY (JSON-friendly) ---')
print(json.dumps(summary, ensure_ascii=False, indent=2))

# print formatted text report
print('\n--- FORMATTED REPORT ---')
print(report.format_financial_summary_text(summary))
