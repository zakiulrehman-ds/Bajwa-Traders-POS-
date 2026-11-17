from django import forms
from .models import Product, Category, Supplier, ShopSetting
class ProductForm(forms.ModelForm):
    class Meta:
        model=Product
        fields=['name','urdu_name','company','category','image','sku','unit','buy_price','sell_price','stock_qty','reorder_level','active']
        widgets={'name':forms.TextInput(attrs={'class':'field'}),'urdu_name':forms.TextInput(attrs={'class':'field','dir':'rtl'}),'company':forms.TextInput(attrs={'class':'field'}),'category':forms.Select(attrs={'class':'field'}),'image':forms.ClearableFileInput(attrs={'class':'field'}),'sku':forms.TextInput(attrs={'class':'field'}),'unit':forms.TextInput(attrs={'class':'field'}),'buy_price':forms.NumberInput(attrs={'class':'field','step':'0.01'}),'sell_price':forms.NumberInput(attrs={'class':'field','step':'0.01'}),'stock_qty':forms.NumberInput(attrs={'class':'field','step':'0.01'}),'reorder_level':forms.NumberInput(attrs={'class':'field','step':'0.01'})}
class CategoryForm(forms.ModelForm):
    class Meta: model=Category; fields=['name','parent','color']
class SupplierForm(forms.ModelForm):
    class Meta: model=Supplier; fields=['name','phone','address','notes']
class SettingForm(forms.ModelForm):
    class Meta: model=ShopSetting; fields=['shop_name','shop_name_urdu','address','phone','receipt_footer','paper_width']
