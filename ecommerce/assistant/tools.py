from django.utils import timezone
from django.db.models import Sum
from ecommerce.models import (
    Product, Customer, Order, Payment, Shipment, ReturnRequest, OrderItem,
    Supplier, PurchaseOrder, Invoice, Refund, Coupon, LoyaltyAccount,
    SupportTicket, Warehouse, WarehouseStock
)


TOOL_REGISTRY = {}
TOOL_SCHEMAS = {}


def register_tool(name, requires_action=False):
    def decorator(fn):
        TOOL_REGISTRY[name] = {'fn': fn, 'requires_action': requires_action}
        return fn
    return decorator


@register_tool('show_suppliers')
def show_suppliers(user, params):
    suppliers = Supplier.objects.all()
    return {'suppliers': list(suppliers.values('id', 'name', 'contact_person', 'phone')[:20])}
 
 
@register_tool('show_open_tickets')
def show_open_tickets(user, params):
    tickets = SupportTicket.objects.exclude(status__in=['resolved', 'closed']).select_related('customer', 'assigned_to')
    return {'tickets': [
        {'id': t.id, 'title': t.title, 'priority': t.priority, 'status': t.status,
         'customer': t.customer.name if t.customer else None,
         'assigned_to': t.assigned_to.username if t.assigned_to else 'Unassigned'}
        for t in tickets[:20]
    ]}
 
 
@register_tool('show_pending_invoices')
def show_pending_invoices(user, params):
    invoices = Invoice.objects.exclude(status='paid').select_related('order', 'order__customer')
    return {'invoices': [
        {'invoice_number': i.invoice_number, 'order': i.order.order_number,
         'customer': i.order.customer.name, 'status': i.status,
         'total': str(i.order.total), 'due_date': str(i.due_date) if i.due_date else None}
        for i in invoices[:20]
    ]}
 
 
@register_tool('show_pending_refunds')
def show_pending_refunds(user, params):
    refunds = Refund.objects.filter(status='pending').select_related('return_request', 'return_request__order')
    return {'refunds': [
        {'order': r.return_request.order.order_number, 'amount': str(r.amount), 'method': r.method}
        for r in refunds[:20]
    ]}
 
 
@register_tool('show_active_coupons')
def show_active_coupons(user, params):
    coupons = Coupon.objects.filter(is_active=True)
    return {'coupons': [
        {'code': c.code, 'type': c.coupon_type, 'value': str(c.value),
         'times_used': c.times_used, 'max_uses': c.max_uses, 'is_valid': c.is_valid()}
        for c in coupons[:20]
    ]}
 
 
@register_tool('show_customer_loyalty')
def show_customer_loyalty(user, params):
    name = params.get('name', '').strip()
    if not name:
        return {'error': 'No customer name provided.'}
    customer = Customer.objects.filter(name__icontains=name).first()
    if not customer:
        return {'error': f'No customer found matching "{name}".'}
    account = getattr(customer, 'loyalty_account', None)
    if not account:
        return {'message': f'{customer.name} does not have a loyalty account yet.'}
    return {
        'customer': customer.name,
        'points_balance': account.points_balance,
        'lifetime_earned': account.lifetime_points_earned,
    }
 
 
@register_tool('show_warehouse_stock')
def show_warehouse_stock(user, params):
    warehouse_name = params.get('warehouse_name', '').strip()
    if warehouse_name:
        warehouse = Warehouse.objects.filter(name__icontains=warehouse_name).first()
        if not warehouse:
            return {'error': f'No warehouse found matching "{warehouse_name}".'}
        stock = WarehouseStock.objects.filter(warehouse=warehouse).select_related('product')
        return {'warehouse': warehouse.name, 'stock': [
            {'product': s.product.name, 'quantity': s.quantity} for s in stock[:20]
        ]}
    warehouses = Warehouse.objects.all()
    return {'warehouses': [{'name': w.name, 'total_units': w.stock.aggregate(t=Sum('quantity'))['t'] or 0} for w in warehouses]}
 
 
@register_tool('show_purchase_orders')
def show_purchase_orders(user, params):
    status = params.get('status')
    pos = PurchaseOrder.objects.select_related('supplier')
    if status:
        pos = pos.filter(status=status)
    return {'purchase_orders': [
        {'po_number': po.po_number, 'supplier': po.supplier.name, 'status': po.status, 'total_cost': str(po.total_cost)}
        for po in pos[:20]
    ]}


@register_tool('show_low_stock')
def show_low_stock(user, params):
    threshold = params.get('threshold', 5)
    products = Product.objects.filter(stock_qty__lte=threshold).order_by('stock_qty')
    return {'products': list(products.values('id', 'name', 'sku', 'stock_qty')[:20])}


@register_tool('show_pending_orders')
def show_pending_orders(user, params):
    orders = Order.objects.filter(status='pending').select_related('customer').order_by('-created_at')
    return {'orders': [
        {'id': o.id, 'order_number': o.order_number, 'customer': o.customer.name, 'total': str(o.total)}
        for o in orders[:20]
    ]}


@register_tool('search_customers_by_name')
def search_customers_by_name(user, params):
    name = params.get('name', '').strip()
    if not name:
        return {'error': 'No name provided to search for.'}
    customers = Customer.objects.filter(name__icontains=name)[:10]
    if not customers:
        return {'customers': [], 'message': f'No customers found matching "{name}".'}
    return {'customers': list(customers.values('id', 'name', 'email', 'phone'))}


@register_tool('search_products_by_name')
def search_products_by_name(user, params):
    name = params.get('name', '').strip()
    if not name:
        return {'error': 'No name provided to search for.'}
    products = Product.objects.filter(name__icontains=name)[:10]
    if not products:
        return {'products': [], 'message': f'No products found matching "{name}".'}
    return {'products': list(products.values('id', 'name', 'sku', 'sale_price', 'stock_qty'))}


@register_tool('show_recent_payments')
def show_recent_payments(user, params):
    status = params.get('status')
    payments = Payment.objects.select_related('order', 'order__customer').order_by('-created_at')
    if status:
        payments = payments.filter(status=status)
    return {'payments': [
        {'order': p.order.order_number, 'customer': p.order.customer.name, 'amount': str(p.amount), 'status': p.status}
        for p in payments[:20]
    ]}


@register_tool('show_order_detail')
def show_order_detail(user, params):
    order_number = params.get('order_number', '').strip()
    if not order_number:
        return {'error': 'No order number provided.'}
    order = Order.objects.filter(order_number__icontains=order_number).select_related('customer').first()
    if not order:
        return {'error': f'No order found matching "{order_number}".'}
    items = [{'product': i.product.name if i.product else 'Deleted product', 'quantity': i.quantity, 'unit_price': str(i.unit_price)} for i in order.items.all()]
    return {
        'order_number': order.order_number,
        'customer': order.customer.name,
        'status': order.get_status_display(),
        'total': str(order.total),
        'items': items,
    }


@register_tool('create_order', requires_action=True)
def create_order(user, params):
    customer_id = params.get('customer_id')
    if not customer_id:
        return {'error': 'A customer_id is required. Use search_customers_by_name first if you only have a name.'}
    customer = Customer.objects.filter(id=customer_id).first()
    if not customer:
        return {'error': 'Customer not found.'}

    product_id = params.get('product_id')
    quantity = params.get('quantity', 1)
    if not product_id:
        return {'error': 'A product_id is required. Use search_products_by_name first if you only have a name.'}
    product = Product.objects.filter(id=product_id).first()
    if not product:
        return {'error': 'Product not found.'}

    import uuid
    from ecommerce.models import OrderItem

    order = Order.objects.create(
        order_number='ORD-' + uuid.uuid4().hex[:8].upper(),
        customer=customer,
        status='pending',
        created_by=user,
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        quantity=quantity,
        unit_price=product.sale_price,
    )
    product.stock_qty = max(0, product.stock_qty - quantity)
    product.save()

    return {'created': True, 'order_number': order.order_number, 'total': str(order.total)}


TOOL_SCHEMAS = {
    "show_low_stock": {
        "type": "function",
        "function": {
            "name": "show_low_stock",
            "description": "Show products with low stock (at or below a threshold, default 5 units).",
            "parameters": {
                "type": "object",
                "properties": {
                    "threshold": {"type": "integer", "description": "Stock level threshold, default 5"}
                },
            },
        }
    },
    "show_pending_orders": {
        "type": "function",
        "function": {
            "name": "show_pending_orders",
            "description": "Show all orders currently in 'pending' status.",
            "parameters": {"type": "object", "properties": {}},
        }
    },
    "search_customers_by_name": {
        "type": "function",
        "function": {
            "name": "search_customers_by_name",
            "description": "Search for customers by name (partial match). Use this before creating an order if you only have a customer's name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Full or partial customer name"}
                },
                "required": ["name"]
            },
        }
    },
    "search_products_by_name": {
        "type": "function",
        "function": {
            "name": "search_products_by_name",
            "description": "Search for products by name (partial match). Use this before creating an order if you only have a product's name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Full or partial product name"}
                },
                "required": ["name"]
            },
        }
    },
    "show_recent_payments": {
        "type": "function",
        "function": {
            "name": "show_recent_payments",
            "description": "Show recent payments, optionally filtered by status (pending, paid, partial, refunded).",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["pending", "paid", "partial", "refunded"]}
                },
            },
        }
    },
    "show_order_detail": {
        "type": "function",
        "function": {
            "name": "show_order_detail",
            "description": "Look up full details of a specific order by its order number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_number": {"type": "string", "description": "Order number, e.g. ORD-A1B2C3D4"}
                },
                "required": ["order_number"]
            },
        }
    },
    "create_order": {
        "type": "function",
        "function": {
            "name": "create_order",
            "description": "Create a new order for a customer with one product. Requires customer_id and product_id — use search_customers_by_name and search_products_by_name first if you only have names.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer", "description": "The customer's ID"},
                    "product_id": {"type": "integer", "description": "The product's ID"},
                    "quantity": {"type": "integer", "description": "Quantity to order, default 1"}
                },
                "required": ["customer_id", "product_id"]
            },
        }
    },
}


TOOL_SCHEMAS.update({
    "show_suppliers": {
        "type": "function",
        "function": {
            "name": "show_suppliers",
            "description": "List all suppliers with their contact info.",
            "parameters": {"type": "object", "properties": {}},
        }
    },
    "show_open_tickets": {
        "type": "function",
        "function": {
            "name": "show_open_tickets",
            "description": "Show support tickets that are still open or in progress (not resolved/closed).",
            "parameters": {"type": "object", "properties": {}},
        }
    },
    "show_pending_invoices": {
        "type": "function",
        "function": {
            "name": "show_pending_invoices",
            "description": "Show invoices that haven't been marked paid yet (draft or sent status).",
            "parameters": {"type": "object", "properties": {}},
        }
    },
    "show_pending_refunds": {
        "type": "function",
        "function": {
            "name": "show_pending_refunds",
            "description": "Show refunds awaiting approval or processing.",
            "parameters": {"type": "object", "properties": {}},
        }
    },
    "show_active_coupons": {
        "type": "function",
        "function": {
            "name": "show_active_coupons",
            "description": "List currently active coupons and their usage.",
            "parameters": {"type": "object", "properties": {}},
        }
    },
    "show_customer_loyalty": {
        "type": "function",
        "function": {
            "name": "show_customer_loyalty",
            "description": "Look up a customer's loyalty points balance by name.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Customer name"}},
                "required": ["name"]
            },
        }
    },
    "show_warehouse_stock": {
        "type": "function",
        "function": {
            "name": "show_warehouse_stock",
            "description": "Show stock levels. If warehouse_name is given, shows that warehouse's product stock; otherwise lists all warehouses with total units.",
            "parameters": {
                "type": "object",
                "properties": {"warehouse_name": {"type": "string", "description": "Optional warehouse name to filter by"}},
            },
        }
    },
    "show_purchase_orders": {
        "type": "function",
        "function": {
            "name": "show_purchase_orders",
            "description": "Show purchase orders, optionally filtered by status (draft, ordered, received, closed).",
            "parameters": {
                "type": "object",
                "properties": {"status": {"type": "string", "enum": ["draft", "ordered", "received", "closed"]}},
            },
        }
    },
})