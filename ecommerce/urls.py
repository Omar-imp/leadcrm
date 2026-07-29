from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.ecommerce_dashboard, name='ecommerce_dashboard'),
    # Customers URLS
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/create/', views.customer_create, name='customer_create'),
    path('customers/bulk-import/', views.bulk_import_customers, name='bulk_import_customers'),

    # Product URLS
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),

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

    #Add Users URLS
    path('users/', views.ecommerce_user_list, name='ecommerce_user_list'),
    path('users/create/', views.ecommerce_user_create, name='ecommerce_user_create'),
    path('users/<int:pk>/edit/', views.ecommerce_user_edit, name='ecommerce_user_edit'),
    path('users/<int:pk>/delete/', views.ecommerce_user_delete, name='ecommerce_user_delete'),
]

