from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required as dj_login_required
from .models import (Customer, Payment, Category, Product,
                    Order, OrderItem, Shipment, ReturnRequest,
                    EcommerceUserPermissions, EcommerceAssistantConversation,
                    EcommerceDocument, Warehouse, StockTransfer, WarehouseStock,
                    Supplier, PurchaseOrder, PurchaseOrderItem,
                    DOCUMENT_TYPE_CHOICES)
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from functools import wraps
from .decorators import block_ecommerce_view_only
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
import csv, json, calendar, io, openpyxl, uuid
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .assistant.service import EcommerceAssistantService


LOGIN_URL = 'ecommerce_login'


def login_required(view_func):
    return dj_login_required(view_func, login_url='ecommerce_login')


def ecommerce_login(request):
    if request.user.is_authenticated:
        return redirect('ecommerce_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('ecommerce_dashboard')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'ecommerce/login.html')


def ecommerce_logout(request):
    logout(request)
    return redirect('login_selector')


@login_required
def ecommerce_dashboard(request):
    today = timezone.localdate()
    week_ago = today - timedelta(days=7)
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    orders = Order.objects.exclude(status='cancelled')

    revenue_today = sum(o.total for o in orders.filter(created_at__date=today))
    revenue_week = sum(o.total for o in orders.filter(created_at__date__gte=week_ago))
    revenue_month = sum(o.total for o in orders.filter(created_at__date__gte=month_start))
    revenue_year = sum(o.total for o in orders.filter(created_at__date__gte=year_start))

    total_orders = orders.count()
    aov = (revenue_month / orders.filter(created_at__date__gte=month_start).count()) if orders.filter(created_at__date__gte=month_start).count() else 0

    new_customers = Customer.objects.filter(created_at__date__gte=month_start).count()
    total_customers = Customer.objects.count()

    open_returns = ReturnRequest.objects.filter(status='pending').count()
    pending_orders = Order.objects.filter(status='pending').count()
    low_stock_products = Product.objects.filter(stock_qty__lte=5).count()

    outstanding_payments = Payment.objects.filter(status__in=['pending', 'partial']).aggregate(total=Sum('amount'))['total'] or 0

    # ── Orders by status (donut chart) ──
    status_labels = []
    status_counts = []
    status_display_map = dict(Order.STATUS_CHOICES)
    status_counts_qs = Order.objects.values('status').annotate(c=Count('id')).order_by('-c')
    for row in status_counts_qs:
        status_labels.append(status_display_map.get(row['status'], row['status']))
        status_counts.append(row['c'])

    # ── Revenue trend last 6 months (bar chart) ──
    month_labels = []
    month_revenue = []
    for i in range(5, -1, -1):
        y, m = today.year, today.month - i
        while m <= 0:
            m += 12
            y -= 1
        month_orders = orders.filter(created_at__year=y, created_at__month=m)
        total = sum(o.total for o in month_orders)
        month_labels.append(f"{calendar.month_abbr[m]} {y}")
        month_revenue.append(float(total))

    context = {
        'active': 'dashboard',
        'revenue_today': revenue_today,
        'revenue_week': revenue_week,
        'revenue_month': revenue_month,
        'revenue_year': revenue_year,
        'total_orders': total_orders,
        'aov': aov,
        'new_customers': new_customers,
        'total_customers': total_customers,
        'open_returns': open_returns,
        'pending_orders': pending_orders,
        'low_stock_products': low_stock_products,
        'outstanding_payments': outstanding_payments,
        'recent_orders': orders.select_related('customer').order_by('-created_at')[:5],
        'status_labels': json.dumps(status_labels),
        'status_counts': json.dumps(status_counts),
        'month_labels': json.dumps(month_labels),
        'month_revenue': json.dumps(month_revenue),
    }
    return render(request, 'ecommerce/dashboard.html', context)


@login_required
def customer_list(request):
    customers = Customer.objects.all().order_by('-created_at')
    context = {
        'customers': customers,
        'active': 'customers',
        'title':'All Customers',
    }
    return render(request, 'ecommerce/customer_list.html', context)


@login_required
@block_ecommerce_view_only
def customer_create(request):
    if request.method == 'POST':
        Customer.objects.create(
            name=request.POST.get('name'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            dob=request.POST.get('dob') or None,
            gender=request.POST.get('gender', ''),
            billing_address=request.POST.get('billing_address', ''),
            shipping_address=request.POST.get('shipping_address', ''),
            tags=request.POST.get('tags', ''),
        )
        messages.success(request, 'Customer created.')
        return redirect('customer_list')

    context = {
        'active': 'customer_create',
        'title': 'Add Customer',
    }
    return render(request, 'ecommerce/customer_form.html', context)


@login_required
@block_ecommerce_view_only
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        customer.name = request.POST.get('name')
        customer.email = request.POST.get('email') or None
        customer.phone = request.POST.get('phone', '')
        customer.dob = request.POST.get('dob') or None
        customer.gender = request.POST.get('gender', '')
        customer.billing_address = request.POST.get('billing_address', '')
        customer.shipping_address = request.POST.get('shipping_address', '')
        customer.tags = request.POST.get('tags', '')
        customer.save()
        messages.success(request, 'Customer updated.')
        return redirect('customer_list')
 
    context = {
        'active': 'customers',
        'title': 'Edit Customer',
        'customer': customer,
    }
    return render(request, 'ecommerce/customer_form.html', context)
 
 
@login_required
@block_ecommerce_view_only
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    customer.delete()
    messages.success(request, 'Customer deleted.')
    return redirect('customer_list')


@login_required
@block_ecommerce_view_only
def bulk_import_customers(request):
    if request.method == 'POST':
        file = request.FILES.get('import_file')
        if not file:
            messages.error(request, 'Please select a CSV or Excel file.')
            return redirect('customer_create')

        filename = file.name.lower()
        rows = []

        try:
            if filename.endswith('.csv'):
                decoded = file.read().decode('utf-8-sig')
                reader = csv.DictReader(io.StringIO(decoded))
                rows = list(reader)
            elif filename.endswith('.xlsx') or filename.endswith('.xls'):
                wb = openpyxl.load_workbook(file, data_only=True)
                ws = wb.active
                headers = [str(cell.value).strip() if cell.value else '' for cell in ws[1]]
                for row in ws.iter_rows(min_row=2, values_only=True):
                    row_dict = dict(zip(headers, row))
                    rows.append(row_dict)
            else:
                messages.error(request, 'Unsupported file type. Please upload a .csv or .xlsx file.')
                return redirect('customer_create')
        except Exception as e:
            messages.error(request, f'Could not read the file: {e}')
            return redirect('customer_create')

        created_count = 0
        skipped_count = 0
        errors = []

        for i, row in enumerate(rows, start=2):
            normalized = {
                str(k).strip().lower().replace(' ', '_'): v
                for k, v in row.items() if k
            }

            name = str(normalized.get('name', '')).strip()
            email = str(normalized.get('email', '')).strip()
            phone = str(normalized.get('phone') or normalized.get('contact_number') or '').strip()
            gender = str(normalized.get('gender', '')).strip()
            billing_address = str(normalized.get('billing_address') or normalized.get('address') or '').strip()
            shipping_address = str(normalized.get('shipping_address', '')).strip()
            tags = str(normalized.get('tags', '')).strip()

            if not name:
                skipped_count += 1
                errors.append(f'Row {i}: missing name, skipped.')
                continue

            try:
                Customer.objects.create(
                    name=name,
                    email=email or None,
                    phone=phone,
                    gender=gender,
                    billing_address=billing_address,
                    shipping_address=shipping_address,
                    tags=tags,
                )
                created_count += 1
            except Exception as e:
                skipped_count += 1
                errors.append(f'Row {i}: {e}')

        if created_count:
            messages.success(request, f'{created_count} customers imported successfully.')
        if skipped_count:
            messages.warning(request, f'{skipped_count} rows skipped.')
        for err in errors[:10]:
            messages.error(request, err)

        return redirect('customer_list')

    return redirect('customer_create')


@login_required
def product_list(request):
    products = Product.objects.select_related('category').order_by('-created_at')
    context = {
        'products': products,
        'active': 'products',
        'title': 'All Products',
    }
    return render(request, 'ecommerce/product_list.html', context)


@login_required
@block_ecommerce_view_only
def product_create(request):
    if request.method == 'POST':
        category_id = request.POST.get('category')
        category = Category.objects.filter(id=category_id).first() if category_id else None
        Product.objects.create(
            name=request.POST.get('name'),
            sku=request.POST.get('sku'),
            barcode=request.POST.get('barcode', ''),
            category=category,
            description=request.POST.get('description', ''),
            cost_price=request.POST.get('cost_price') or 0,
            sale_price=request.POST.get('sale_price') or 0,
            stock_qty=request.POST.get('stock_qty') or 0,
        )
        messages.success(request, 'Product created.')
        return redirect('product_list')

    context = {
        'active': 'product_create',
        'title': 'Add Product',
        'categories': Category.objects.all(),
    }
    return render(request, 'ecommerce/product_form.html', context) 


@login_required
def category_list(request):
    categories = Category.objects.select_related('parent').order_by('name')
    context = {
        'categories': categories,
        'active': 'categories',
        'title': 'All Categories',
    }
    return render(request, 'ecommerce/category_list.html', context)

 
@login_required
@block_ecommerce_view_only
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        category_id = request.POST.get('category')
        category = Category.objects.filter(id=category_id).first() if category_id else None
        product.name = request.POST.get('name')
        product.sku = request.POST.get('sku')
        product.barcode = request.POST.get('barcode', '')
        product.category = category
        product.description = request.POST.get('description', '')
        product.cost_price = request.POST.get('cost_price') or 0
        product.sale_price = request.POST.get('sale_price') or 0
        product.stock_qty = request.POST.get('stock_qty') or 0
        product.save()
        messages.success(request, 'Product updated.')
        return redirect('product_list')
 
    context = {
        'active': 'products',
        'title': 'Edit Product',
        'product': product,
        'categories': Category.objects.all(),
    }
    return render(request, 'ecommerce/product_form.html', context)
 
 
@login_required
@block_ecommerce_view_only
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    messages.success(request, 'Product deleted.')
    return redirect('product_list')


@login_required
@block_ecommerce_view_only
def category_create(request):
    if request.method == 'POST':
        parent_id = request.POST.get('parent')
        parent = Category.objects.filter(id=parent_id).first() if parent_id else None
        Category.objects.create(
            name=request.POST.get('name'),
            parent=parent,
        )
        messages.success(request, 'Category created.')
        return redirect('category_list')

    context = {
        'active': 'category_create',
        'title': 'Add Category',
        'categories': Category.objects.all(),
    }
    return render(request, 'ecommerce/category_form.html', context)


@login_required
def order_list(request):
    orders = Order.objects.select_related('customer').order_by('-created_at')
    context = {
        'orders': orders,
        'active': 'orders',
        'title': 'All Orders',
    }
    return render(request, 'ecommerce/order_list.html', context)


@login_required
@block_ecommerce_view_only
def order_create(request):
    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        customer = Customer.objects.filter(id=customer_id).first()
        if not customer:
            messages.error(request, 'Please select a valid customer.')
            return redirect('order_create')

        order = Order.objects.create(
            order_number='ORD-' + uuid.uuid4().hex[:8].upper(),
            customer=customer,
            status=request.POST.get('status', 'pending'),
            discount=request.POST.get('discount') or 0,
            tax=request.POST.get('tax') or 0,
            shipping_cost=request.POST.get('shipping_cost') or 0,
            created_by=request.user,
        )

        product_ids = request.POST.getlist('product')
        quantities = request.POST.getlist('quantity')

        for product_id, qty in zip(product_ids, quantities):
            if not product_id or not qty:
                continue
            product = Product.objects.filter(id=product_id).first()
            if product:
                qty_int = int(qty)
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=qty_int,
                    unit_price=product.sale_price,
                )
                product.stock_qty = max(0, product.stock_qty - qty_int)
                product.save()

        messages.success(request, f'Order {order.order_number} created.')
        return redirect('order_list')

    context = {
        'active': 'orders',
        'title': 'Create Order',
        'customers': Customer.objects.all(),
        'products': Product.objects.all(),
    }
    return render(request, 'ecommerce/order_form.html', context)


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    context = {
        'order': order,
        'active': 'orders',
        'title': f'Order {order.order_number}',
    }
    return render(request, 'ecommerce/order_detail.html', context)


@login_required
def low_stock_list(request):
    threshold = 5
    products = Product.objects.filter(stock_qty__lte=threshold).order_by('stock_qty')
    context = {
        'products': products,
        'active': 'low_stock',
        'title': 'Low Stock Products',
        'threshold': threshold,
    }
    return render(request, 'ecommerce/low_stock_list.html', context)


@login_required
def payment_list(request):
    payments = Payment.objects.select_related('order', 'order__customer').order_by('-created_at')
    context = {
        'payments': payments,
        'active': 'payments',
        'title': 'All Payments',
    }
    return render(request, 'ecommerce/payment_list.html', context)


@login_required
@block_ecommerce_view_only
def payment_create(request, order_id=None):
    order = get_object_or_404(Order, id=order_id) if order_id else None

    if request.method == 'POST':
        order_pk = request.POST.get('order') or order_id
        order_obj = get_object_or_404(Order, id=order_pk)
        Payment.objects.create(
            order=order_obj,
            method=request.POST.get('method', 'cash'),
            status=request.POST.get('status', 'pending'),
            amount=request.POST.get('amount') or 0,
        )
        messages.success(request, 'Payment recorded.')
        return redirect('order_detail', pk=order_obj.pk)

    context = {
        'active': 'payment_create',
        'title': 'Record Payment',
        'order': order,
        'orders': Order.objects.all(),
    }
    return render(request, 'ecommerce/payment_form.html', context)


@login_required
def shipment_list(request):
    shipments = Shipment.objects.select_related('order', 'order__customer').order_by('-created_at')
    context = {
        'shipments': shipments,
        'active': 'shipping',
        'title': 'All Shipments',
    }
    return render(request, 'ecommerce/shipment_list.html', context)


@login_required
@block_ecommerce_view_only
def shipment_create(request, order_id=None):
    order = get_object_or_404(Order, id=order_id) if order_id else None

    if request.method == 'POST':
        order_pk = request.POST.get('order') or order_id
        order_obj = get_object_or_404(Order, id=order_pk)
        shipment = Shipment.objects.create(
            order=order_obj,
            tracking_number=request.POST.get('tracking_number', ''),
            carrier=request.POST.get('carrier', ''),
            status=request.POST.get('status', 'pickup'),
        )
        if shipment.status == 'delivered':
            order_obj.status = 'delivered'
        elif shipment.status == 'in_transit':
            order_obj.status = 'shipped'
        order_obj.save()

        messages.success(request, 'Shipment created.')
        return redirect('order_detail', pk=order_obj.pk)

    context = {
        'active': 'shipment_create',
        'title': 'Create Shipment',
        'order': order,
        'orders': Order.objects.all(),
    }
    return render(request, 'ecommerce/shipment_form.html', context)


@login_required
def return_list(request):
    returns = ReturnRequest.objects.select_related('order', 'order__customer', 'product').order_by('-created_at')
    context = {
        'returns': returns,
        'active': 'support',
        'title': 'Return Requests',
    }
    return render(request, 'ecommerce/return_list.html', context)


@login_required
@block_ecommerce_view_only
def return_create(request, order_id=None):
    order = get_object_or_404(Order, id=order_id) if order_id else None

    if request.method == 'POST':
        order_pk = request.POST.get('order') or order_id
        order_obj = get_object_or_404(Order, id=order_pk)
        product_id = request.POST.get('product')
        product = Product.objects.filter(id=product_id).first() if product_id else None

        ReturnRequest.objects.create(
            order=order_obj,
            product=product,
            reason=request.POST.get('reason', ''),
            status='pending',
        )
        messages.success(request, 'Return request created.')
        return redirect('return_list')

    context = {
        'active': 'support',
        'title': 'Create Return Request',
        'order': order,
        'orders': Order.objects.all(),
        'products': Product.objects.all(),
    }
    return render(request, 'ecommerce/return_form.html', context)


@login_required
@block_ecommerce_view_only
def return_update_status(request, pk):
    ret = get_object_or_404(ReturnRequest, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(ReturnRequest.STATUS_CHOICES):
            ret.status = new_status
            ret.save()
            messages.success(request, f'Return status updated to {ret.get_status_display()}.')
    return redirect('return_list')


SECTION_LABELS = {
    'dashboard': 'Dashboard',
    'products': 'Products',
    'categories': 'Categories',
    'customers': 'Customers',
    'orders': 'Orders',
    'inventory': 'Inventory',
    'payments': 'Payments',
    'shipping': 'Shipping',
    'returns': 'Returns',
    'reports': 'Reports',
}


@login_required
def ecommerce_user_list(request):
    users = User.objects.all().order_by('username')
    context = {'users': users, 'active': 'users', 'title': 'Users'}
    return render(request, 'ecommerce/user_list.html', context)


@login_required
def ecommerce_user_create(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.save()
            _save_ecommerce_permissions(user, request.POST)
            messages.success(request, f'User {username} created.')
            return redirect('ecommerce_user_list')

    return render(request, 'ecommerce/user_form.html', {
        'active': 'users',
        'title': 'Create User',
        'section_labels': SECTION_LABELS,
    })


@login_required
def ecommerce_user_edit(request, pk):
    target_user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        target_user.email = request.POST.get('email')
        target_user.first_name = request.POST.get('first_name')
        target_user.last_name = request.POST.get('last_name')
        target_user.save()
        _save_ecommerce_permissions(target_user, request.POST)
        messages.success(request, 'User updated.')
        return redirect('ecommerce_user_list')

    perms, _ = EcommerceUserPermissions.objects.get_or_create(user=target_user)
    return render(request, 'ecommerce/user_form.html', {
        'active': 'users',
        'title': 'Edit User',
        'edit_user': target_user,
        'section_labels': SECTION_LABELS,
        'current_perms': perms,
    })


def _save_ecommerce_permissions(user, post_data):
    perms, _ = EcommerceUserPermissions.objects.get_or_create(user=user)
    for section in EcommerceUserPermissions.ALL_SECTIONS:
        value = post_data.get(f'perm_{section}', 'none')
        if value in ['full', 'view', 'none']:
            setattr(perms, section, value)
    perms.save()


@login_required
def ecommerce_user_delete(request, pk):
    target_user = get_object_or_404(User, pk=pk)
    if target_user == request.user:
        messages.error(request, "You can't delete your own account.")
    else:
        target_user.delete()
        messages.success(request, 'User deleted.')
    return redirect('ecommerce_user_list')


@login_required
def ecommerce_assistant_config(request):
    perms, _ = EcommerceUserPermissions.objects.get_or_create(user=request.user)
    access = 'full' if request.user.is_superuser else perms.chatbot
    return JsonResponse({'access': access})


@login_required
@require_POST
def ecommerce_assistant_chat(request):
    data = json.loads(request.body)
    message = data.get('message', '').strip()
    conversation_id = data.get('conversation_id')

    if not message:
        return JsonResponse({'error': 'Empty message'}, status=400)

    service = EcommerceAssistantService(request.user)
    if not service.can_query():
        return JsonResponse({'error': 'You do not have access to this assistant.'}, status=403)

    result = service.handle_message(message, conversation_id)
    return JsonResponse(result)


@login_required
def ecommerce_assistant_history(request, conversation_id):
    conversation = EcommerceAssistantConversation.objects.filter(id=conversation_id, user=request.user).first()
    if not conversation:
        return JsonResponse({'messages': []})
    msgs = list(conversation.messages.values('role', 'content', 'created_at'))
    return JsonResponse({'messages': msgs})


# ── ADD TO ecommerce/views.py ──

# ── REPLACE in ecommerce/views.py ──

import json
import calendar as cal_module


@login_required
def ecommerce_reports(request):
    today = timezone.localdate()
    this_month = today.replace(day=1)

    orders = Order.objects.exclude(status='cancelled')
    total_revenue = sum(o.total for o in orders)
    revenue_this_month = sum(o.total for o in orders.filter(created_at__date__gte=this_month))

    # orders by status -> donut chart data
    status_labels = []
    status_counts = []
    status_display_map = dict(Order.STATUS_CHOICES)
    for key, label in Order.STATUS_CHOICES:
        c = Order.objects.filter(status=key).count()
        if c > 0:
            status_labels.append(label)
            status_counts.append(c)

    # revenue trend last 6 months -> bar chart data
    month_labels = []
    month_revenue = []
    for i in range(5, -1, -1):
        y, m = today.year, today.month - i
        while m <= 0:
            m += 12
            y -= 1
        month_orders = orders.filter(created_at__year=y, created_at__month=m)
        total = sum(o.total for o in month_orders)
        month_labels.append(f"{cal_module.month_abbr[m]} {y}")
        month_revenue.append(float(total))

    # best sellers
    best_sellers = (
        OrderItem.objects.values('product__name')
        .annotate(total_qty=Sum('quantity'))
        .order_by('-total_qty')[:8]
    )
    best_seller_labels = [b['product__name'] or 'Unknown' for b in best_sellers]
    best_seller_counts = [b['total_qty'] for b in best_sellers]

    # top customers
    top_customers = []
    for c in Customer.objects.all():
        c_orders = Order.objects.filter(customer=c).exclude(status='cancelled')
        total = sum(o.total for o in c_orders)
        if total > 0:
            top_customers.append({'name': c.name, 'orders': c_orders.count(), 'total': total})
    top_customers.sort(key=lambda x: x['total'], reverse=True)
    top_customers = top_customers[:10]

    total_products = Product.objects.count()
    low_stock_count = Product.objects.filter(stock_qty__lte=5).count()

    payments = Payment.objects.all()
    paid_total = payments.filter(status='paid').aggregate(t=Sum('amount'))['t'] or 0
    pending_total = payments.filter(status__in=['pending', 'partial']).aggregate(t=Sum('amount'))['t'] or 0

    context = {
        'active': 'reports',
        'title': 'Reports & Analytics',
        'total_revenue': total_revenue,
        'revenue_this_month': revenue_this_month,
        'top_customers': top_customers,
        'total_products': total_products,
        'low_stock_count': low_stock_count,
        'paid_total': paid_total,
        'pending_total': pending_total,
        'status_labels': json.dumps(status_labels),
        'status_counts': json.dumps(status_counts),
        'month_labels': json.dumps(month_labels),
        'month_revenue': json.dumps(month_revenue),
        'best_seller_labels': json.dumps(best_seller_labels),
        'best_seller_counts': json.dumps(best_seller_counts),
    }
    return render(request, 'ecommerce/reports.html', context)


@login_required
def stock_overview(request):
    products = Product.objects.select_related('category').order_by('-stock_qty')
    total_units = sum(p.stock_qty for p in products)
    total_value = sum(p.stock_qty * p.sale_price for p in products)

    # stock health breakdown -> donut chart
    out_of_stock = products.filter(stock_qty=0).count()
    low_stock = products.filter(stock_qty__gt=0, stock_qty__lte=5).count()
    healthy_stock = products.filter(stock_qty__gt=5).count()

    health_labels = json.dumps(['Healthy', 'Low Stock', 'Out of Stock'])
    health_counts = json.dumps([healthy_stock, low_stock, out_of_stock])

    # top 8 products by stock value -> bar chart
    by_value = sorted(products, key=lambda p: p.stock_qty * p.sale_price, reverse=True)[:8]
    value_labels = json.dumps([p.name for p in by_value])
    value_amounts = json.dumps([float(p.stock_qty * p.sale_price) for p in by_value])

    context = {
        'products': products,
        'active': 'stock_overview',
        'title': 'Stock Overview',
        'total_units': total_units,
        'total_value': total_value,
        'out_of_stock': out_of_stock,
        'low_stock': low_stock,
        'healthy_stock': healthy_stock,
        'health_labels': health_labels,
        'health_counts': health_counts,
        'value_labels': value_labels,
        'value_amounts': value_amounts,
    }
    return render(request, 'ecommerce/stock_overview.html', context)

@login_required
def order_list_filtered(request, status):
    orders = Order.objects.filter(status=status).select_related('customer').order_by('-created_at')
    title_map = {'pending': 'Pending Orders', 'shipped': 'Shipped Orders'}
    context = {
        'orders': orders,
        'active': 'orders',
        'title': title_map.get(status, 'Orders'),
    }
    return render(request, 'ecommerce/order_list.html', context)


@login_required
@block_ecommerce_view_only
def document_upload(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        doc_type = request.POST.get('doc_type', 'other')
        notes = request.POST.get('notes')
        file = request.FILES.get('file')

        if not file:
            messages.error(request, 'Please select a file to upload.')
            return redirect('document_upload')

        doc = EcommerceDocument(
            title=title or file.name,
            doc_type=doc_type,
            notes=notes,
            uploaded_by=request.user,
            file=file,
        )
        order_id = request.POST.get('order')
        customer_id = request.POST.get('customer')
        doc.order_id = order_id if order_id else None
        doc.customer_id = customer_id if customer_id else None
        doc.save()
        messages.success(request, f'"{doc.title}" uploaded successfully.')
        return redirect('document_list')

    context = {
        'active': 'documents',
        'title': 'Upload Document',
        'doc_types': DOCUMENT_TYPE_CHOICES,
        'orders': Order.objects.all(),
        'customers': Customer.objects.all(),
        'recent_documents': EcommerceDocument.objects.order_by('-created_at')[:5],
    }
    return render(request, 'ecommerce/document_upload.html', context)


@login_required
def document_list(request):
    documents = EcommerceDocument.objects.select_related('order', 'customer', 'uploaded_by').order_by('-created_at')
    doc_type = request.GET.get('type')
    if doc_type:
        documents = documents.filter(doc_type=doc_type)
    context = {
        'documents': documents,
        'active': 'documents',
        'title': 'Documents',
        'doc_types': DOCUMENT_TYPE_CHOICES,
        'selected_type': doc_type,
    }
    return render(request, 'ecommerce/document_list.html', context)


@login_required
@block_ecommerce_view_only
def document_delete(request, pk):
    doc = get_object_or_404(EcommerceDocument, pk=pk)
    doc.file.delete()
    doc.delete()
    messages.success(request, 'Document deleted.')
    return redirect('document_list')


@login_required
def warehouse_list(request):
    warehouses = Warehouse.objects.all()
    data = []
    for w in warehouses:
        total_units = w.stock.aggregate(t=Sum('quantity'))['t'] or 0
        data.append({'warehouse': w, 'total_units': total_units, 'product_lines': w.stock.count()})
    context = {'warehouses': data, 'active': 'warehouses', 'title': 'Warehouses'}
    return render(request, 'ecommerce/warehouse_list.html', context)


@login_required
@block_ecommerce_view_only
def warehouse_create(request):
    if request.method == 'POST':
        Warehouse.objects.create(
            name=request.POST.get('name'),
            address=request.POST.get('address', ''),
        )
        messages.success(request, 'Warehouse created.')
        return redirect('warehouse_list')
    return render(request, 'ecommerce/warehouse_form.html', {
        'active': 'warehouses',
        'title': 'Add Warehouse',
        'existing_warehouses': Warehouse.objects.all(),
    })


@login_required
def warehouse_detail(request, pk):
    warehouse = get_object_or_404(Warehouse, pk=pk)
    stock = warehouse.stock.select_related('product').order_by('-quantity')
    context = {
        'warehouse': warehouse,
        'stock': stock,
        'active': 'warehouses',
        'title': warehouse.name,
    }
    return render(request, 'ecommerce/warehouse_detail.html', context)


@login_required
def stock_transfer_list(request):
    transfers = StockTransfer.objects.select_related('product', 'from_warehouse', 'to_warehouse').order_by('-created_at')
    context = {'transfers': transfers, 'active': 'stock_transfers', 'title': 'Stock Transfers'}
    return render(request, 'ecommerce/stock_transfer_list.html', context)


@login_required
@block_ecommerce_view_only
def stock_transfer_create(request):
    if request.method == 'POST':
        product_id = request.POST.get('product')
        from_id = request.POST.get('from_warehouse')
        to_id = request.POST.get('to_warehouse')
        quantity = int(request.POST.get('quantity', 0))

        if from_id == to_id:
            messages.error(request, 'Source and destination warehouses must be different.')
            return redirect('stock_transfer_create')
        
        product = get_object_or_404(Product, pk=product_id)
        from_wh = get_object_or_404(Warehouse, pk=from_id)
        to_wh   = get_object_or_404(Warehouse, pk=to_id)

        from_stock, _ = WarehouseStock.objects.get_or_create(warehouse=from_wh, product=product)
        if from_stock.quantity < quantity:
            messages.error(request, f'Not enough stock in {from_wh.name} ({from_stock.quantity} available).')
            return redirect('stock_transfer_create')
 
        from_stock.quantity -= quantity
        from_stock.save()
 
        to_stock, _ = WarehouseStock.objects.get_or_create(warehouse=to_wh, product=product)
        to_stock.quantity += quantity
        to_stock.save()

        StockTransfer.objects.create(
            product=product, from_warehouse=from_wh, to_warehouse=to_wh,
            quantity=quantity, status='completed', created_by=request.user,
        )
        messages.success(request, f'Transferred {quantity} x {product.name} from {from_wh.name} to {to_wh.name}.')
        return redirect('stock_transfer_list')

    context = {
        'active': 'warehouses',
        'title': 'New Stock Transfer',
        'products': Product.objects.all(),
        'warehouses': Warehouse.objects.all(),
    }
    return render(request, 'ecommerce/stock_transfer_form.html', context)


@login_required
def supplier_list(request):
    suppliers = Supplier.objects.all().order_by('name')
    context = {'suppliers': suppliers, 'active': 'suppliers', 'title': 'Suppliers'}
    return render(request, 'ecommerce/supplier_list.html', context)
 
 
@login_required
@block_ecommerce_view_only
def supplier_create(request):
    if request.method == 'POST':
        Supplier.objects.create(
            name=request.POST.get('name'),
            contact_person=request.POST.get('contact_person', ''),
            email=request.POST.get('email') or None,
            phone=request.POST.get('phone', ''),
            address=request.POST.get('address', ''),
        )
        messages.success(request, 'Supplier created.')
        return redirect('supplier_list')
    context = {
        'active': 'supplier_create',
        'title': 'Add Supplier',
        'existing_suppliers': Supplier.objects.all(),
    }
    return render(request, 'ecommerce/supplier_form.html', context)
 
 
@login_required
@block_ecommerce_view_only
def supplier_edit(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        supplier.name = request.POST.get('name')
        supplier.contact_person = request.POST.get('contact_person', '')
        supplier.email = request.POST.get('email') or None
        supplier.phone = request.POST.get('phone', '')
        supplier.address = request.POST.get('address', '')
        supplier.save()
        messages.success(request, 'Supplier updated.')
        return redirect('supplier_list')
    context = {
        'active': 'suppliers',
        'title': 'Edit Supplier',
        'supplier': supplier,
        'existing_suppliers': Supplier.objects.exclude(pk=pk),
    }
    return render(request, 'ecommerce/supplier_form.html', context)
 
 
@login_required
@block_ecommerce_view_only
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    supplier.delete()
    messages.success(request, 'Supplier deleted.')
    return redirect('supplier_list')
 
 
@login_required
def purchase_order_list(request):
    pos = PurchaseOrder.objects.select_related('supplier').order_by('-created_at')
    context = {'purchase_orders': pos, 'active': 'purchase_orders', 'title': 'Purchase Orders'}
    return render(request, 'ecommerce/purchase_order_list.html', context)
 
 
@login_required
@block_ecommerce_view_only
def purchase_order_create(request):
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        supplier = get_object_or_404(Supplier, pk=supplier_id)
 
        po = PurchaseOrder.objects.create(
            po_number='PO-' + uuid.uuid4().hex[:8].upper(),
            supplier=supplier,
            status=request.POST.get('status', 'draft'),
            created_by=request.user,
        )
 
        product_ids = request.POST.getlist('product')
        quantities = request.POST.getlist('quantity')
        unit_costs = request.POST.getlist('unit_cost')
 
        for product_id, qty, cost in zip(product_ids, quantities, unit_costs):
            if not product_id or not qty:
                continue
            product = Product.objects.filter(id=product_id).first()
            if product:
                PurchaseOrderItem.objects.create(
                    purchase_order=po,
                    product=product,
                    quantity=int(qty),
                    unit_cost=cost or 0,
                )
 
        messages.success(request, f'Purchase Order {po.po_number} created.')
        return redirect('purchase_order_detail', pk=po.pk)
 
    context = {
        'active': 'purchase_order_create',
        'title': 'Create Purchase Order',
        'suppliers': Supplier.objects.all(),
        'products': Product.objects.all(),
    }
    return render(request, 'ecommerce/purchase_order_form.html', context)
 
 
@login_required
def purchase_order_detail(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    context = {'po': po, 'active': 'purchase_orders', 'title': f'Purchase Order {po.po_number}'}
    return render(request, 'ecommerce/purchase_order_detail.html', context)
 
 
@login_required
@block_ecommerce_view_only
def purchase_order_receive(request, pk):
    """Marks a PO as received and adds its items to product stock."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    if po.status == 'received':
        messages.info(request, 'This purchase order was already marked received.')
        return redirect('purchase_order_detail', pk=pk)
 
    for item in po.items.all():
        if item.product:
            item.product.stock_qty += item.quantity
            item.product.save()
 
    po.status = 'received'
    po.save()
    messages.success(request, f'{po.po_number} received — stock updated.')
    return redirect('purchase_order_detail', pk=pk)