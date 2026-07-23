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
