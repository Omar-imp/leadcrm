from django.db import models
from django.contrib.auth.models import User


class Organization(models.Model):
    PRODUCT_CHOICES = [
        ('leads', 'Lead CRM'),
        ('ecommerce', 'E-commerce CRM'),
        ('both', 'Both'),
    ]

    name         = models.CharField(max_length=150)
    product_type = models.CharField(max_length=15, choices=PRODUCT_CHOICES, default='leads')
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class OrganizationMembership(models.Model):
    """Links a Django User to an Organization, so we know which org's data they see."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='org_membership')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='members')

    def __str__(self):
        return f"{self.user.username} → {self.organization.name}"
    

class Customer(models.Model):
    name             = models.CharField(max_length=150)
    email            = models.EmailField(blank=True, null=True)
    phone            = models.CharField(max_length=30, blank=True)
    dob              = models.DateField(blank=True, null=True)
    gender           = models.CharField(max_length=10, blank=True)
    billing_address  = models.TextField(blank=True)
    shipping_address = models.TextField(blank=True)
    tags             = models.CharField(max_length=200, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    

class Category(models.Model):
    name = models.CharField(max_length=150)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children')

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, unique=True)
    barcode = models.CharField(max_length=100, blank=True)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name='products')
    description = models.TextField(blank=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_qty = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'), ('pending', 'Pending'), ('confirmed', 'Confirmed'),
        ('packed', 'Packed'), ('shipped', 'Shipped'), ('delivered', 'Delivered'),
        ('returned', 'Returned'), ('refunded', 'Refunded'), ('cancelled', 'Cancelled'),
    ]
    order_number = models.CharField(max_length=30, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='draft')
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def subtotal(self):
        return sum(item.quantity * item.unit_price for item in self.items.all())

    @property
    def total(self):
        return self.subtotal - self.discount + self.tax + self.shipping_cost

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product} x{self.quantity}"
    

class Payment(models.Model):
    METHOD_CHOICES = [
        ('cash', 'Cash'), ('bank_transfer', 'Bank Transfer'),
        ('stripe', 'Stripe'), ('paypal', 'PayPal'), ('cod', 'COD'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('paid', 'Paid'),
        ('partial', 'Partial'), ('refunded', 'Refunded'),
    ]
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='cash')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order.order_number} - {self.amount}"
    

class Shipment(models.Model):
    STATUS_CHOICES = [
        ('pickup', 'Pickup'), ('in_transit', 'In Transit'), ('delivered', 'Delivered'),
    ]
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='shipments')
    tracking_number = models.CharField(max_length=100, blank=True)
    carrier = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pickup')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.order.order_number} - {self.tracking_number or 'no tracking'}"
    

class ReturnRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('approved', 'Approved'),
        ('rejected', 'Rejected'), ('refunded', 'Refunded'),
    ]
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='returns')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Return for {self.order.order_number}"


ECOMMERCE_SECTIONS = [
    'dashboard', 'products', 'categories', 'customers',
    'orders', 'inventory', 'payments', 'shipping', 'returns',
    'reports', 'chatbot', 'suppliers', 'support'
]


class EcommerceUserPermissions(models.Model):
    ACCESS_CHOICES = [('none', 'No Access'), ('view', 'View Only'), ('full', 'Full Access')]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='ecommerce_permissions')
    dashboard = models.CharField(max_length=10, choices=ACCESS_CHOICES, default='none')
    products = models.CharField(max_length=10, choices=ACCESS_CHOICES, default='none')
    categories = models.CharField(max_length=10, choices=ACCESS_CHOICES, default='none')
    customers = models.CharField(max_length=10, choices=ACCESS_CHOICES, default='none')
    orders = models.CharField(max_length=10, choices=ACCESS_CHOICES, default='none')
    inventory = models.CharField(max_length=10, choices=ACCESS_CHOICES, default='none')
    payments = models.CharField(max_length=10, choices=ACCESS_CHOICES, default='none')
    shipping = models.CharField(max_length=10, choices=ACCESS_CHOICES, default='none')
    returns = models.CharField(max_length=10, choices=ACCESS_CHOICES, default='none')
    reports = models.CharField(max_length=10, choices=ACCESS_CHOICES, default='none')
    chatbot = models.CharField(max_length=10, choices=ACCESS_CHOICES, default='none')
    suppliers = models.CharField(max_length=10, choices=ACCESS_CHOICES, default='none')
    support = models.CharField(max_length=10, choices=ACCESS_CHOICES, default='none')

    ALL_SECTIONS = ECOMMERCE_SECTIONS

    def get_section_permission(self, section: str) -> str:
        return getattr(self, section, 'none')

    def has_access(self, section: str) -> bool:
        return self.get_section_permission(section) in ['full', 'view']

    def is_view_only(self, section: str) -> bool:
        return self.get_section_permission(section) == 'view'

    def has_full_access(self, section: str) -> bool:
        return self.get_section_permission(section) == 'full'

    def __str__(self):
        return f"E-commerce Permissions for {self.user.username}"


class EcommerceAssistantConversation(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ecommerce_assistant_conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class EcommerceAssistantMessage(models.Model):
    conversation = models.ForeignKey(EcommerceAssistantConversation, on_delete=models.CASCADE, related_name='messages')
    role         = models.CharField(max_length=10)
    content      = models.TextField()
    created_at   = models.DateTimeField(auto_now_add=True)


class EcommerceAssistantAuditLog(models.Model):
    user            = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    query           = models.TextField()
    action_executed = models.CharField(max_length=100)
    success         = models.BooleanField(default=True)
    response        = models.TextField(blank=True)
    timestamp       = models.DateTimeField(auto_now_add=True)


DOCUMENT_TYPE_CHOICES = [
    ('invoice', 'Invoice'),
    ('receipt', 'Receipt'),
    ('contract', 'Contract'),
    ('id_proof', 'ID Proof'),
    ('other', 'Other'),
]

class EcommerceDocument(models.Model):
    title       = models.CharField(max_length=200)
    doc_type    = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES, default='other')
    file        = models.FileField(upload_to='ecommerce_documents/')
    order       = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    customer    = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes       = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Warehouse(models.Model):
    name       = models.CharField(max_length=150)
    address    = models.TextField(blank=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    

class WarehouseStock(models.Model):
    """Tracks how many units of each product sit in each warehouse."""
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stock')
    product   = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='warehouse_stock')
    quantity  = models.IntegerField(default=0)

    class Meta:
        unique_together = ('warehouse', 'product')

    def __str__(self):
        return f"{self.product.name} @ {self.warehouse.name}: {self.quantity}"


class StockTransfer(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'), ('in_transit', 'In Transit'), ('completed', 'Completed')]

    product        = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='transfers')
    from_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='transfers_out')
    to_warehouse   = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='transfers_in')
    quantity       = models.IntegerField()
    status         = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    created_by     = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name}: {self.from_warehouse} -> {self.to_warehouse} ({self.quantity})"
    

class Supplier(models.Model):
    name = models.CharField(max_length=150)
    contact_person = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
 
    def __str__(self):
        return self.name
 
 
class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'), ('ordered', 'Ordered'),
        ('received', 'Received'), ('closed', 'Closed'),
    ]
    po_number = models.CharField(max_length=30, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
 
    @property
    def total_cost(self):
        return sum(item.quantity * item.unit_cost for item in self.items.all())
 
    def __str__(self):
        return self.po_number
 
 
class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField(default=1)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
 
    def __str__(self):
        return f"{self.product} x{self.quantity}"


class Invoice(models.Model):
    STATUS_CHOICES = [('draft', 'Draft'), ('sent', 'Sent'), ('paid', 'Paid'), ('overdue', 'Overdue')]

    invoice_number = models.CharField(max_length=30, unique=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='invoices')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='draft')
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.invoice_number


class Refund(models.Model):
    METHOD_CHOICES = [
        ('original_payment', 'Original Payment Method'), ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'), ('store_credit', 'Store Credit'),
    ]
    STATUS_CHOICES = [('pending', 'Pending'), ('approved', 'Approved'), ('completed', 'Completed'), ('rejected', 'Rejected')]

    return_request = models.ForeignKey(ReturnRequest, on_delete=models.CASCADE, related_name='refunds')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='original_payment')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Refund Rs {self.amount} for {self.return_request.order.order_number}"


TICKET_STATUS_CHOICES = [
    ('open', 'Open'), ('in_progress', 'In Progress'),
    ('resolved', 'Resolved'), ('closed', 'Closed'),
]
TICKET_PRIORITY_CHOICES = [
    ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical'),
]


class SupportTicket(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=TICKET_STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=10, choices=TICKET_PRIORITY_CHOICES, default='medium')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_ecom_tickets')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_ecom_tickets')
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class TicketReply(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reply on {self.ticket.title}"


class EcommerceNotification(models.Model):
    NOTIF_TYPE_CHOICES = [
        ('ticket_assigned', 'Ticket Assigned'),
        ('order_pending', 'Order Pending'),
        ('low_stock', 'Low Stock'),
        ('payment_received', 'Payment Received'),
        ('return_requested', 'Return Requested'),
        ('other', 'Other'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ecommerce_notifications')
    notif_type = models.CharField(max_length=30, choices=NOTIF_TYPE_CHOICES, default='other')
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title