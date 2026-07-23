from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Customer
from django.shortcuts import redirect
from django.contrib import messages
import csv
import io
import openpyxl
from .models import Category, Product

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