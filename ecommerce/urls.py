from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.ecommerce_dashboard, name='ecommerce_dashboard'),
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/create/', views.customer_create, name='customer_create'),
    path('customers/bulk-import/', views.bulk_import_customers, name='bulk_import_customers'),
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
]   
