import base64
import csv
import json
import socket
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO
from urllib.parse import urlsplit, urlunsplit

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Count, F, Sum
from django.db.models.deletion import ProtectedError
from django.db.models.functions import TruncDate, TruncMonth
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .forms import CategoryForm, ProductForm, SettingForm, SupplierForm
from .models import (
    Category,
    MasterReceipt,
    Product,
    Purchase,
    PurchaseItem,
    Sale,
    SaleItem,
    ShopSetting,
    StockMovement,
    Supplier,
)


def owner_required(user):
    return user.is_superuser or user.is_staff


def base_context():
    return {
        'shop': ShopSetting.current(),
        'low_stock_count': Product.objects.filter(
            active=True,
            stock_qty__lte=F('reorder_level'),
        ).count(),
    }


@login_required
def dashboard(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)

    sales_today = Sale.objects.filter(created_at__date=today).aggregate(v=Sum('total'))['v'] or 0
    sales_month = Sale.objects.filter(created_at__date__gte=month_start).aggregate(v=Sum('total'))['v'] or 0
    purchases_month = Purchase.objects.filter(created_at__date__gte=month_start).aggregate(v=Sum('total'))['v'] or 0
    profit = (
        SaleItem.objects.filter(sale__created_at__date__gte=month_start)
        .aggregate(v=Sum(F('line_total') - F('unit_cost') * F('qty')))['v']
        or 0
    )

    daily = list(
        Sale.objects.filter(created_at__date__gte=today - timedelta(days=13))
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(total=Sum('total'))
        .order_by('day')
    )
    categories_data = list(
        SaleItem.objects.values('product__category__name')
        .annotate(total=Sum('line_total'))
        .order_by('-total')[:8]
    )
    top = list(
        SaleItem.objects.values('product__name')
        .annotate(qty=Sum('qty'), revenue=Sum('line_total'))
        .order_by('-qty')[:6]
    )

    context = base_context() | {
        'sales_today': sales_today,
        'sales_month': sales_month,
        'purchases_month': purchases_month,
        'profit': profit,
        'product_count': Product.objects.filter(active=True).count(),
        'stock_value': sum(
            (p.buy_price * p.stock_qty for p in Product.objects.filter(active=True)),
            Decimal('0'),
        ),
        'low_stock': Product.objects.filter(active=True, stock_qty__lte=F('reorder_level'))[:8],
        'recent_sales': Sale.objects.order_by('-created_at')[:7],
        'daily_json': json.dumps([
            {'day': x['day'].strftime('%d %b'), 'total': float(x['total'])}
            for x in daily
        ]),
        'category_json': json.dumps([
            {'name': x['product__category__name'] or 'Uncategorised', 'total': float(x['total'])}
            for x in categories_data
        ]),
        'top_json': json.dumps([
            {'name': x['product__name'], 'qty': float(x['qty'])}
            for x in top
        ]),
    }
    return render(request, 'core/dashboard.html', context)


@login_required
@ensure_csrf_cookie
def pos(request):
    products_qs = Product.objects.filter(active=True).select_related('category')
    cats = Category.objects.filter(parent__isnull=True)
    return render(request, 'core/pos.html', base_context() | {
        'products': products_qs,
        'categories': cats,
    })


@login_required
@require_POST
def checkout(request):
    try:
        data = json.loads(request.body)
        lines = data.get('items', [])
    except Exception:
        return HttpResponseBadRequest('Invalid bill data')

    if not lines:
        return JsonResponse({'ok': False, 'error': 'Cart is empty.'}, status=400)

    try:
        discount = Decimal(str(data.get('discount', 0)))
        paid = Decimal(str(data.get('paid', 0)))
        if discount < 0 or paid < 0:
            raise InvalidOperation

        with transaction.atomic():
            subtotal = Decimal('0')
            prepared = []
            for line in lines:
                product = Product.objects.select_for_update().get(pk=int(line['id']), active=True)
                qty = Decimal(str(line['qty']))
                if qty <= 0 or product.stock_qty < qty:
                    return JsonResponse(
                        {
                            'ok': False,
                            'error': f'Insufficient stock for {product.name}. Available: {product.stock_qty}.',
                        },
                        status=400,
                    )
                amount = (product.sell_price * qty).quantize(Decimal('.01'))
                subtotal += amount
                prepared.append((product, qty, amount))

            total = max(Decimal('0'), subtotal - discount).quantize(Decimal('.01'))
            if paid < total:
                return JsonResponse(
                    {'ok': False, 'error': 'Cash received is less than the bill total.'},
                    status=400,
                )

            sale = Sale.objects.create(
                customer_name=data.get('customer', '')[:140],
                customer_phone=data.get('phone', '')[:40],
                discount=discount,
                subtotal=subtotal,
                total=total,
                paid=paid,
                change=paid - total,
                cashier=request.user,
            )
            for product, qty, amount in prepared:
                SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    qty=qty,
                    unit_price=product.sell_price,
                    unit_cost=product.buy_price,
                    line_total=amount,
                )
                product.stock_qty -= qty
                product.save(update_fields=['stock_qty'])
                StockMovement.objects.create(
                    product=product,
                    qty=-qty,
                    reason='sale',
                    reference=sale.bill_no,
                )

        return JsonResponse({
            'ok': True,
            'receipt_url': f'/sales/{sale.pk}/receipt/?autoprint=1',
            'bill_no': sale.bill_no,
        })
    except (Product.DoesNotExist, KeyError, ValueError, InvalidOperation):
        return JsonResponse(
            {'ok': False, 'error': 'Please check the selected products and quantities.'},
            status=400,
        )


@login_required
def products(request):
    qs = Product.objects.select_related('category').all()
    q = request.GET.get('q', '').strip()
    cat = request.GET.get('category', '')

    if q:
        qs = qs.filter(name__icontains=q) | Product.objects.filter(sku__icontains=q)
    if cat.isdigit():
        qs = qs.filter(category_id=int(cat))

    context = base_context() | {
        'products': qs,
        'categories': Category.objects.all(),
        'q': q,
        'selected_category': cat,
    }
    if request.headers.get('HX-Request') == 'true':
        return render(request, 'core/product_table.html', context)
    return render(request, 'core/products.html', context)


@login_required
def product_add(request):
    form = ProductForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        product = form.save()
        if product.stock_qty:
            StockMovement.objects.create(
                product=product,
                qty=product.stock_qty,
                reason='adjustment',
                reference='OPENING',
                note='Opening stock',
            )
        messages.success(request, 'Product added successfully.')
        return redirect('products')
    return render(request, 'core/product_form.html', base_context() | {
        'form': form,
        'heading': 'Add product',
    })


@login_required
def product_edit(request, pk):
    obj = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, request.FILES or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Product updated.')
        return redirect('products')
    return render(request, 'core/product_form.html', base_context() | {
        'form': form,
        'heading': 'Edit product',
    })


@login_required
@require_POST
def product_delete(request, pk):
    get_object_or_404(Product, pk=pk).delete()
    messages.success(request, 'Product removed.')
    return redirect('products')


@login_required
def categories(request):
    form = CategoryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Category saved.')
        return redirect('categories')

    cats = Category.objects.select_related('parent').annotate(
        product_count=Count('products', distinct=True),
        child_count=Count('children', distinct=True),
    )
    return render(request, 'core/categories.html', base_context() | {
        'form': form,
        'categories': cats,
        'editing': None,
    })


@login_required
def category_edit(request, pk):
    obj = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        updated = form.save(commit=False)
        if updated.parent_id == obj.pk:
            messages.error(request, 'A category cannot be its own parent.')
            return redirect('category_edit', pk=pk)
        updated.save()
        messages.success(request, 'Category updated.')
        return redirect('categories')

    cats = Category.objects.select_related('parent').annotate(
        product_count=Count('products', distinct=True),
        child_count=Count('children', distinct=True),
    )
    return render(request, 'core/categories.html', base_context() | {
        'form': form,
        'categories': cats,
        'editing': obj,
    })


@login_required
@require_POST
def category_delete(request, pk):
    obj = get_object_or_404(Category, pk=pk)
    prod_count = obj.products.count()
    sub_count = obj.children.count()
    if prod_count > 0 or sub_count > 0:
        messages.error(
            request,
            f'Cannot delete "{obj.name}" because it has {prod_count} product(s) and {sub_count} subcategory(ies). Reassign or remove them first.',
        )
        return redirect('categories')

    obj.delete()
    messages.success(request, f'Category "{obj.name}" deleted.')
    return redirect('categories')


@login_required
def suppliers(request):
    form = SupplierForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Supplier added.')
        return redirect('suppliers')
    return render(request, 'core/suppliers.html', base_context() | {
        'form': form,
        'suppliers': Supplier.objects.all().order_by('name'),
        'editing': None,
    })


@login_required
def supplier_edit(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, f'Supplier "{supplier.name}" updated.')
            return redirect('suppliers')
    else:
        form = SupplierForm(instance=supplier)

    return render(request, 'core/suppliers.html', base_context() | {
        'form': form,
        'suppliers': Supplier.objects.all().order_by('name'),
        'editing': supplier,
    })


@login_required
@require_POST
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    name = supplier.name
    try:
        supplier.delete()
        messages.success(request, f'Supplier "{name}" deleted.')
    except ProtectedError:
        messages.error(request, f'Cannot delete "{name}" because purchase records are linked to this supplier.')
    return redirect('suppliers')


@login_required
def inventory(request):
    if request.method == 'POST':
        try:
            product = Product.objects.get(pk=request.POST.get('product'))
            qty = Decimal(request.POST.get('qty', '0'))
            direction = request.POST.get('direction', 'add')
            if qty <= 0:
                raise ValueError

            delta = qty if direction == 'add' else -qty
            if product.stock_qty + delta < 0:
                raise ValueError

            with transaction.atomic():
                product.stock_qty += delta
                product.save(update_fields=['stock_qty'])
                StockMovement.objects.create(
                    product=product,
                    qty=delta,
                    reason='adjustment',
                    reference='MANUAL',
                    note=request.POST.get('note', 'Manual stock adjustment'),
                )
            messages.success(request, 'Stock adjustment saved.')
            return redirect('inventory')
        except Exception:
            messages.error(
                request,
                'Please select a product and enter a valid quantity. Stock cannot become negative.',
            )

    movements = StockMovement.objects.select_related('product').order_by('-created_at')[:100]
    return render(request, 'core/inventory.html', base_context() | {
        'products': Product.objects.filter(active=True),
        'movements': movements,
        'stock_products': Product.objects.filter(active=True).select_related('category').order_by('name'),
    })


@login_required
def purchases(request):
    return render(request, 'core/purchases.html', base_context() | {
        'purchases': Purchase.objects.select_related('supplier').order_by('-created_at')[:100],
    })


@login_required
def purchase_add(request):
    if request.method == 'POST':
        try:
            ids = request.POST.getlist('product')
            qtys = request.POST.getlist('qty')
            costs = request.POST.getlist('cost')
            rows = []
            for pid, q, c in zip(ids, qtys, costs):
                if pid and q and c and Decimal(q) > 0:
                    rows.append((Product.objects.get(pk=pid), Decimal(q), Decimal(c)))
            if not rows:
                raise ValueError

            with transaction.atomic():
                purchase = Purchase.objects.create(
                    supplier_id=request.POST.get('supplier') or None,
                    invoice_no=request.POST.get('invoice_no', ''),
                    paid_amount=Decimal(request.POST.get('paid') or 0),
                    note=request.POST.get('note', ''),
                )
                total = Decimal('0')
                for p, q, c in rows:
                    line = q * c
                    total += line
                    PurchaseItem.objects.create(
                        purchase=purchase,
                        product=p,
                        qty=q,
                        unit_cost=c,
                        line_total=line,
                    )
                    p.stock_qty += q
                    p.buy_price = c
                    p.save(update_fields=['stock_qty', 'buy_price'])
                    StockMovement.objects.create(
                        product=p,
                        qty=q,
                        reason='purchase',
                        reference=f'PUR-{purchase.pk}',
                    )
                purchase.total = total
                purchase.save(update_fields=['total'])

            messages.success(request, 'Purchase saved and stock updated.')
            return redirect('purchases')
        except Exception:
            messages.error(request, 'Please add at least one valid product row and check quantities and costs.')

    return render(request, 'core/purchase_form.html', base_context() | {
        'products': Product.objects.filter(active=True),
        'suppliers': Supplier.objects.all(),
    })


@login_required
def sales(request):
    return render(request, 'core/sales.html', base_context() | {
        'sales': Sale.objects.order_by('-created_at')[:150],
    })


@login_required
def receipt(request, pk):
    sale = get_object_or_404(Sale.objects.prefetch_related('items__product'), pk=pk)
    shop = ShopSetting.current()
    try:
        import qrcode

        qr_url = request.build_absolute_uri(reverse('receipt', args=[sale.pk]))
        parts = urlsplit(qr_url)
        if parts.hostname in ('localhost', '127.0.0.1', '0.0.0.0'):
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.connect(('192.0.2.1', 80))
                lan_ip = sock.getsockname()[0]
                if lan_ip and not lan_ip.startswith('127.'):
                    netloc = lan_ip + (f':{parts.port}' if parts.port else '')
                    qr_url = urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
            finally:
                sock.close()

        qr = qrcode.make(qr_url, box_size=5, border=2)
        b = BytesIO()
        qr.save(b, format='PNG')
        qr_data = 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()
    except Exception:
        qr_data = ''

    return render(request, 'core/receipt.html', {
        'sale': sale,
        'shop': shop,
        'qr_data': qr_data,
    })


@login_required
def reports(request):
    today = timezone.localdate()
    start = request.GET.get('start', (today - timedelta(days=29)).isoformat())
    end = request.GET.get('end', today.isoformat())

    qs = Sale.objects.filter(created_at__date__gte=start, created_at__date__lte=end)
    totals = qs.aggregate(sales=Sum('total'), bills=Count('id'))
    rows = list(
        qs.annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(total=Sum('total'))
        .order_by('day')
    )

    return render(request, 'core/reports.html', base_context() | {
        'start': start,
        'end': end,
        'totals': totals,
        'rows': rows,
        'chart_json': json.dumps([
            {'day': r['day'].strftime('%d %b'), 'total': float(r['total'])}
            for r in rows
        ]),
        'top_products': (
            SaleItem.objects.filter(sale__in=qs)
            .values('product__name')
            .annotate(qty=Sum('qty'), revenue=Sum('line_total'))
            .order_by('-revenue')[:10]
        ),
        'stock': (
            Product.objects.filter(active=True)
            .select_related('category')
            .order_by('stock_qty')[:30]
        ),
    })


@login_required
def settings_view(request):
    obj = ShopSetting.current()
    form = SettingForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Shop settings updated.')
        return redirect('settings')
    return render(request, 'core/settings.html', base_context() | {'form': form})


@login_required
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_info':
            username = request.POST.get('username', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()

            if not username:
                messages.error(request, 'Username cannot be empty.')
            elif user.__class__.objects.filter(username=username).exclude(pk=user.pk).exists():
                messages.error(request, 'That username is already taken.')
            else:
                user.username = username
                user.first_name = first_name
                user.last_name = last_name
                user.email = email
                user.save()
                messages.success(request, 'Profile details updated.')
            return redirect('profile')

        elif action == 'change_password':
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')

            if not user.check_password(current_password):
                messages.error(request, 'Current password is incorrect.')
            elif len(new_password) < 6:
                messages.error(request, 'New password must be at least 6 characters.')
            elif new_password != confirm_password:
                messages.error(request, 'New passwords do not match.')
            else:
                user.set_password(new_password)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password changed successfully.')
            return redirect('profile')

    return render(request, 'core/profile.html', base_context())


def manifest(request):
    return JsonResponse({
        'name': 'Bajwa Traders',
        'short_name': 'Bajwa Traders',
        'start_url': '/',
        'display': 'standalone',
        'background_color': '#f5f7fb',
        'theme_color': '#123c32',
        'icons': [],
    })

@login_required
def master_receipts(request):
    assigned_ids = MasterReceipt.sales.through.objects.values_list('sale_id', flat=True)
    available_sales = Sale.objects.exclude(pk__in=assigned_ids).order_by('-created_at')[:200]
    masters = MasterReceipt.objects.prefetch_related('sales').order_by('-created_at')[:50]
    return render(request, 'core/master_receipts.html', base_context() | {
        'available_sales': available_sales,
        'master_receipts': masters,
    })


@login_required
@require_POST
def master_receipt_create(request):
    raw_ids = request.POST.getlist('sale_ids')
    ids = list(dict.fromkeys(int(x) for x in raw_ids if x.isdigit()))
    if len(ids) < 1:
        messages.error(request, 'Select at least one customer receipt.')
        return redirect('master_receipts')
    with transaction.atomic():
        already_assigned = MasterReceipt.sales.through.objects.filter(sale_id__in=ids).exists()
        if already_assigned:
            messages.error(request, 'One or more selected bills are already included in a master receipt.')
            return redirect('master_receipts')
        selected = list(Sale.objects.filter(pk__in=ids).prefetch_related('items__product'))
        if len(selected) != len(ids):
            messages.error(request, 'One or more selected bills could not be found.')
            return redirect('master_receipts')
        master = MasterReceipt.objects.create(created_by=request.user, note=request.POST.get('note', '')[:500])
        master.sales.set(selected)
    return redirect('master_receipt_detail', pk=master.pk)


@login_required
def master_receipt_detail(request, pk):
    master = get_object_or_404(MasterReceipt.objects.prefetch_related('sales__items__product'), pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(MasterReceipt.STATUS_CHOICES):
            master.status = new_status
            master.save(update_fields=['status'])
            messages.success(request, 'Master receipt status updated.')
            return redirect('master_receipt_detail', pk=master.pk)

    product_totals = {}
    sales = list(master.sales.all().order_by('created_at'))
    for sale in sales:
        for line in sale.items.all():
            key = line.product_id
            if key not in product_totals:
                product_totals[key] = {
                    'name': line.product.urdu_name or line.product.name,
                    'unit': line.product.unit,
                    'qty': Decimal('0'),
                    'amount': Decimal('0'),
                }
            product_totals[key]['qty'] += line.qty
            product_totals[key]['amount'] += line.line_total
    return render(request, 'core/master_receipt_detail.html', base_context() | {
        'master': master,
        'sales': sales,
        'product_totals': list(product_totals.values()),
        'grand_total': sum((sale.total for sale in sales), Decimal('0.00')),
        'total_units': sum((x['qty'] for x in product_totals.values()), Decimal('0')),
    })
