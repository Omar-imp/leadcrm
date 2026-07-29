from django.utils import timezone
from django.db.models import Sum
from ecommerce.models import Product, Customer, Order, Payment, Shipment, ReturnRequest


TOOL_REGISTRY = {}
TOOL_SCHEMAS = {}


def register_tool(name, requires_action=False):
    def decorator(fn):
        TOOL_REGISTRY[name] = {'fn': fn, 'requires_action': requires_action}
        return fn
    return decorator


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
