from src.inventory.product_manager import ProductManager
from src.sales.transaction_manager import TransactionManager
from src.report_and_sreach import report
from pathlib import Path

pm = ProductManager(storage_file=Path('data_test_products.json'))
# reset products and categories for a clean test
pm.products = []
pm.category_mgr = pm.category_mgr
# ensure categories exist for test
pm.category_mgr._names = ['Drinks','Household']
pm.category_mgr._rebuild_normalized_cache()
# add sample products
pm.add_product('P1','Milk','Drinks',10000,15000,50,5,'box')
pm.add_product('P2','Soap','Household',2000,3000,100,10,'piece')

# create transaction manager with in-memory transactions
class DummyTM:
    def __init__(self):
        self.transactions = []
    def list_transactions(self):
        return list(self.transactions)

from src.sales.transaction import Transaction
from datetime import datetime

tm = DummyTM()
# add some export transactions
now = datetime.now()

tm.transactions.append(Transaction(transaction_id='T1',product_id='P1',trans_type='EXPORT',quantity=10,date=now))
tm.transactions.append(Transaction(transaction_id='T2',product_id='P2',trans_type='EXPORT',quantity=2,date=now))

res = report.compute_financial_summary(pm, tm, top_k=3)
print(res)
print(report.format_financial_summary_text(res))
