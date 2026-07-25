from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import (Customer, Payment, Category, Product,
                    Order, OrderItem)
from django.contrib import messages
import csv
import io
import openpyxl
import uuid

@login_required
def ecommerce_dashboard(request):
    context = {
        'active': 'dashboard'
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
        'active': 'customers',
        'title': 'Add Customer',
    }
    return render(request, 'ecommerce/customer_form.html', context)


@login_required
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
        'active': 'products',
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
        'active': 'categories',
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
        'active': 'inventory',
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
        'active': 'payments',
        'title': 'Record Payment',
        'order': order,
        'orders': Order.objects.all(),
    }
    return render(request, 'ecommerce/payment_form.html', context)