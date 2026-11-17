from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import uuid

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children')
    color = models.CharField(max_length=20, default='#2563eb')
    def __str__(self): return self.name

class Product(models.Model):
    name = models.CharField(max_length=180)
    urdu_name = models.CharField(max_length=180, blank=True)
    company = models.CharField(max_length=120, blank=True)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name='products')
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    sku = models.CharField(max_length=60, blank=True, unique=True, null=True)
    unit = models.CharField(max_length=30, default='pcs')
    buy_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sell_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reorder_level = models.DecimalField(max_digits=12, decimal_places=2, default=5)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['name']
    def __str__(self): return self.name
    @property
    def low_stock(self): return self.stock_qty <= self.reorder_level

class Supplier(models.Model):
    name = models.CharField(max_length=160)
    phone = models.CharField(max_length=40, blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    def __str__(self): return self.name

class Purchase(models.Model):
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.SET_NULL)
    invoice_no = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    note = models.TextField(blank=True)
    def __str__(self): return f'Purchase #{self.pk}'

class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    qty = models.DecimalField(max_digits=12, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

class StockMovement(models.Model):
    REASONS = [('purchase','Purchase'),('sale','Sale'),('adjustment','Adjustment'),('return','Return')]
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='movements')
    qty = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=20, choices=REASONS)
    reference = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    note = models.CharField(max_length=240, blank=True)

class Sale(models.Model):
    bill_no = models.CharField(max_length=24, unique=True, blank=True)
    customer_name = models.CharField(max_length=140, blank=True)
    customer_phone = models.CharField(max_length=40, blank=True)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    change = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cashier = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(default=timezone.now)
    def save(self,*args,**kwargs):
        if not self.bill_no: self.bill_no = f'BT-{timezone.now():%y%m%d}-{uuid.uuid4().hex[:6].upper()}'
        super().save(*args,**kwargs)
    def __str__(self): return self.bill_no

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    qty = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

class ShopSetting(models.Model):
    shop_name = models.CharField(max_length=160, default='Bajwa Traders')
    shop_name_urdu = models.CharField(max_length=160, default='باجوہ ٹریڈرز')
    address = models.CharField(max_length=240, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    receipt_footer = models.CharField(max_length=240, default='آپ کا شکریہ! دوبارہ تشریف لائیں')
    paper_width = models.CharField(max_length=4, choices=[('58mm','58mm'),('80mm','80mm')], default='80mm')
    @classmethod
    def current(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
