from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Core Workspace & POS
    path('', views.dashboard, name='dashboard'),
    path('pos/', views.pos, name='pos'),
    path('pos/checkout/', views.checkout, name='checkout'),
    path('pos/master-receipts/', views.master_receipts, name='master_receipts'),
    path('pos/master-receipts/create/', views.master_receipt_create, name='master_receipt_create'),
    path('pos/master-receipts/<int:pk>/', views.master_receipt_detail, name='master_receipt_detail'),

    # Products
    path('products/', views.products, name='products'),
    path('products/add/', views.product_add, name='product_add'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),

    # Categories
    path('categories/', views.categories, name='categories'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    # Stock & Purchases
    path('inventory/', views.inventory, name='inventory'),
    path('purchases/', views.purchases, name='purchases'),
    path('purchases/add/', views.purchase_add, name='purchase_add'),

    # Suppliers
    path('suppliers/', views.suppliers, name='suppliers'),
    path('suppliers/<int:pk>/edit/', views.supplier_edit, name='supplier_edit'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),

    # Sales, Reports, Settings & Profile
    path('sales/', views.sales, name='sales'),
    path('sales/<int:pk>/receipt/', views.receipt, name='receipt'),
    path('reports/', views.reports, name='reports'),
    path('settings/', views.settings_view, name='settings'),
    path('profile/', views.profile_view, name='profile'),
    path('manifest.json', views.manifest, name='manifest'),
]