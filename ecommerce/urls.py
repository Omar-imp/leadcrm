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
]   
