from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser, SkinListing, Order, Deposit


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """Admin interface for CustomUser model."""
    list_display = ['username', 'steam_id', 'email', 'balance_active', 'balance_frozen', 'is_staff']
    list_filter = ['is_staff', 'is_superuser', 'is_active']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Steam Information', {
            'fields': ('steam_id', 'steam_api_key', 'trade_url')
        }),
        ('Wallet Information', {
            'fields': ('wallet_address', 'balance_active', 'balance_frozen')
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Steam Information', {
            'fields': ('steam_id', 'steam_api_key', 'trade_url')
        }),
        ('Wallet Information', {
            'fields': ('wallet_address',)
        }),
    )


@admin.register(SkinListing)
class SkinListingAdmin(admin.ModelAdmin):
    """Admin interface for SkinListing model."""
    list_display = ['market_name', 'seller', 'price_ton', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['market_name', 'asset_id', 'seller__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin interface for Order model."""
    list_display = ['id', 'buyer', 'seller', 'listing', 'amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['buyer__username', 'seller__username', 'steam_trade_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    """Admin interface for Deposit model."""
    list_display = ['id', 'user', 'amount', 'tx_hash', 'status', 'comment_code', 'created_at', 'confirmed_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'tx_hash', 'comment_code']
    readonly_fields = ['created_at', 'updated_at', 'confirmed_at']
    date_hierarchy = 'created_at'
