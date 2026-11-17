from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import Category, Product, Sale, SaleItem, StockMovement
from decimal import Decimal

class ShopModelTests(TestCase):
    def test_product_low_stock_flag(self):
        category=Category.objects.create(name='Cold Drinks')
        product=Product.objects.create(name='Cola 1.5L',category=category,stock_qty=2,reorder_level=5)
        self.assertTrue(product.low_stock)

    def test_sale_bill_number_is_generated(self):
        sale=Sale.objects.create(total=Decimal('100'),paid=Decimal('100'))
        self.assertTrue(sale.bill_no.startswith('BT-'))

class AuthenticationTests(TestCase):
    def test_dashboard_requires_login(self):
        response=self.client.get('/')
        self.assertEqual(response.status_code,302)
