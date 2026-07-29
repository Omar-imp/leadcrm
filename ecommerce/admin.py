from django.contrib import admin
from .models import Organization, OrganizationMembership, Customer, Category, Product, Order, OrderItem, Payment, Shipment, ReturnRequest, EcommerceUserPermissions


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_type', 'created_at')


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization')


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'created_at')
    search_fields = ('name', 'email', 'phone')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'sale_price', 'stock_qty')
    search_fields = ('name', 'sku')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'customer', 'status', 'total', 'created_at')
    search_fields = ('order_number', 'customer__name')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'method', 'status', 'amount', 'created_at')


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ('order', 'tracking_number', 'carrier', 'status', 'updated_at')


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'status', 'created_at')


@admin.register(EcommerceUserPermissions)
class EcommerceUserPermissionsAdmin(admin.ModelAdmin):
    list_display = ('user', 'products', 'orders', 'customers', 'shipping')
    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Access Levels', {
            'fields': ('dashboard', 'products', 'categories', 'customers', 'orders', 'inventory', 'payments', 'shipping', 'returns', 'reports')
        }),
    )
