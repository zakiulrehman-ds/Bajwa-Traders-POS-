from django.contrib import admin
from .models import Category, Product, Supplier, Purchase, PurchaseItem, StockMovement, Sale, SaleItem, ShopSetting
admin.site.register([Category, Product, Supplier, Purchase, PurchaseItem, StockMovement, Sale, SaleItem, ShopSetting])
