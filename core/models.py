from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class CustomUser(AbstractUser):
    """
    Custom user model extending AbstractUser for P2P CS2 Skin Marketplace.
    """
    steam_id = models.CharField(max_length=255, unique=True, blank=True, null=True, help_text="Steam ID of the user", db_index=True)
    steam_api_key = models.CharField(max_length=255, blank=True, help_text="Steam API key (should be encrypted in production)")
    trade_url = models.CharField(max_length=500, blank=True, help_text="Steam trade URL")
    wallet_address = models.CharField(max_length=255, blank=True, help_text="TON wallet address for withdrawals")
    balance_active = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Active balance available for use"
    )
    balance_frozen = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Frozen balance (held in escrow)"
    )

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.username} ({self.steam_id})"


class SkinListing(models.Model):
    """
    Model representing a CS2 skin listing on the marketplace.
    """
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('SOLD', 'Sold'),
        ('CANCELLED', 'Cancelled'),
    ]

    seller = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='listings',
        help_text="User who listed the skin"
    )
    asset_id = models.CharField(
        max_length=255,
        help_text="Steam Item Asset ID"
    )
    market_name = models.CharField(
        max_length=255,
        help_text="Market name of the skin item"
    )
    price_ton = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Price in TON"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE',
        help_text="Current status of the listing"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Skin Listing"
        verbose_name_plural = "Skin Listings"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.market_name} - {self.seller.username} ({self.status})"


class Order(models.Model):
    """
    Model representing an order/transaction in the marketplace.
    """
    STATUS_CHOICES = [
        ('PAID', 'Paid'),
        ('SENT', 'Sent'),
        ('COMPLETED', 'Completed'),
        ('RELEASED', 'Released'),
        ('DISPUTED', 'Disputed'),
    ]

    buyer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='orders_as_buyer',
        help_text="User who purchased the skin"
    )
    seller = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='orders_as_seller',
        help_text="User who sold the skin"
    )
    listing = models.ForeignKey(
        SkinListing,
        on_delete=models.CASCADE,
        related_name='orders',
        help_text="The skin listing this order is for"
    )
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Order amount in TON"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PAID',
        help_text="Current status of the order"
    )
    steam_trade_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Steam trade offer ID"
    )
    hold_expiry_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date when the escrow hold expires"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} - {self.buyer.username} -> {self.seller.username} ({self.status})"


class Deposit(models.Model):
    """
    Model representing a TON deposit transaction.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='deposits',
        help_text="User who made the deposit"
    )
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Deposit amount in TON"
    )
    tx_hash = models.CharField(
        max_length=255,
        unique=True,
        help_text="Blockchain transaction hash"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text="Current status of the deposit"
    )
    comment_code = models.CharField(
        max_length=255,
        help_text="Unique comment code used for deposit identification"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True, help_text="When the deposit was confirmed")

    class Meta:
        verbose_name = "Deposit"
        verbose_name_plural = "Deposits"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tx_hash']),
            models.Index(fields=['status']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"Deposit #{self.id} - {self.user.username} - {self.amount} TON ({self.status})"
