from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.ecommerce_dashboard, name='ecommerce_dashboard'),

    # Customers URLS
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/create/', views.customer_create, name='customer_create'),
    path('customers/bulk-import/', views.bulk_import_customers, name='bulk_import_customers'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),

    # Product URLS
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),

    # Category and Order URLS
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/create/', views.order_create, name='order_create'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),

    path('inventory/low-stock/', views.low_stock_list, name='low_stock_list'),

    # Payment URLS
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/create/', views.payment_create, name='payment_create'),
    path('orders/<int:order_id>/pay/', views.payment_create, name='payment_create_for_order'),

    # Shipment URLS
    path('shipments/', views.shipment_list, name='shipment_list'),
    path('shipments/create/', views.shipment_create, name='shipment_create'),
    path('orders/<int:order_id>/ship/', views.shipment_create, name='shipment_create_for_order'),

    # Return URLS
    path('returns/', views.return_list, name='return_list'),
    path('returns/create/', views.return_create, name='return_create'),
    path('orders/<int:order_id>/return/', views.return_create, name='return_create_for_order'),
    path('returns/<int:pk>/update-status/', views.return_update_status, name='return_update_status'),

    # Login/Logout URLS
    path('login/', views.ecommerce_login, name='ecommerce_login'),
    path('logout/', views.ecommerce_logout, name='ecommerce_logout'),

    # Add Users URLS
    path('users/', views.ecommerce_user_list, name='ecommerce_user_list'),
    path('users/create/', views.ecommerce_user_create, name='ecommerce_user_create'),
    path('users/<int:pk>/edit/', views.ecommerce_user_edit, name='ecommerce_user_edit'),
    path('users/<int:pk>/delete/', views.ecommerce_user_delete, name='ecommerce_user_delete'),
    
    # Chatbot URLS
    path('assistant/config/', views.ecommerce_assistant_config, name='ecommerce_assistant_config'),
    path('assistant/chat/', views.ecommerce_assistant_chat, name='ecommerce_assistant_chat'),
    path('assistant/history/<int:conversation_id>/', views.ecommerce_assistant_history, name='ecommerce_assistant_history'),

    path('reports/', views.ecommerce_reports, name='ecommerce_reports'),
    path('inventory/stock-overview/', views.stock_overview, name='stock_overview'),
    path('orders/status/<str:status>/', views.order_list_filtered, name='order_list_filtered'),

    # Docs URLS 
    path('documents/', views.document_list, name='document_list'),
    path('documents/upload/', views.document_upload, name='document_upload'),
    path('documents/<int:pk>/delete/', views.document_delete, name='document_delete'),

    # Warehouse URLS
    path('warehouses/', views.warehouse_list, name='warehouse_list'),
    path('warehouses/create/', views.warehouse_create, name='warehouse_create'),
    path('warehouses/<int:pk>/', views.warehouse_detail, name='warehouse_detail'),
    path('warehouses/transfers/', views.stock_transfer_list, name='stock_transfer_list'),
    path('warehouses/transfers/create/', views.stock_transfer_create, name='stock_transfer_create'),

    # Supplier and Purchase URLS
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/create/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/edit/', views.supplier_edit, name='supplier_edit'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),
    path('purchase-orders/', views.purchase_order_list, name='purchase_order_list'),
    path('purchase-orders/create/', views.purchase_order_create, name='purchase_order_create'),
    path('purchase-orders/<int:pk>/', views.purchase_order_detail, name='purchase_order_detail'),
    path('purchase-orders/<int:pk>/receive/', views.purchase_order_receive, name='purchase_order_receive'),

    # Invoice and Refund URLS
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/create/', views.invoice_create, name='invoice_create'),
    path('orders/<int:order_id>/invoice/', views.invoice_create, name='invoice_create_for_order'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/status/<str:status>/', views.invoice_status, name='invoice_status'),
    path('invoices/<int:pk>/pdf/', views.invoice_pdf, name='invoice_pdf'),
    path('refunds/', views.refund_list, name='refund_list'),
    path('refunds/create/', views.refund_create, name='refund_create'),
    path('returns/<int:return_id>/refund/', views.refund_create, name='refund_create_for_return'),
    path('refunds/<int:pk>/status/<str:status>/', views.refund_status, name='refund_status'),

    # Tickets and Notification URLS
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('tickets/create/', views.ticket_create, name='ticket_create'),
    path('tickets/<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('tickets/<int:pk>/delete/', views.ticket_delete, name='ticket_delete'),
    path('notifications/', views.notification_list, name='ecom_notification_list'),
    path('notifications/<int:pk>/read/', views.notification_read, name='ecom_notification_read'),
    path('notifications/read-all/', views.notification_read_all, name='ecom_notification_read_all'),

    # Coupons and Loyalty URLS
    path('coupons/', views.coupon_list, name='coupon_list'),
    path('coupons/create/', views.coupon_create, name='coupon_create'),
    path('coupons/<int:pk>/toggle/', views.coupon_toggle, name='coupon_toggle'),
    path('coupons/<int:pk>/delete/', views.coupon_delete, name='coupon_delete'),
    path('loyalty/', views.loyalty_list, name='loyalty_list'),
    path('loyalty/<int:pk>/', views.loyalty_detail, name='loyalty_detail'),
    path('loyalty/<int:pk>/adjust/', views.loyalty_adjust, name='loyalty_adjust'),
    path('loyalty/create/<int:customer_id>/', views.loyalty_create_for_customer, name='loyalty_create_for_customer'),

    #  Abondoned Cart and Reviews URLS
    path('abandoned-carts/', views.abandoned_cart_list, name='abandoned_cart_list'),
    path('abandoned-carts/create/', views.abandoned_cart_create, name='abandoned_cart_create'),
    path('abandoned-carts/<int:pk>/status/<str:status>/', views.abandoned_cart_status, name='abandoned_cart_status'),
    path('reviews/', views.review_list, name='review_list'),
    path('reviews/create/', views.review_create, name='review_create'),
    path('reviews/<int:pk>/approve/', views.review_approve, name='review_approve'),
    path('reviews/<int:pk>/delete/', views.review_delete, name='review_delete'),
]

