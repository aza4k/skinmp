from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.conf import settings as django_settings
from django.db import transaction
from decimal import Decimal, InvalidOperation
from .models import CustomUser, SkinListing, Deposit, Order
from services.steam_service import get_user_inventory
from core.services.balance_service import get_user_comment_code


def home(request):
    """
    Home page showing active listings.
    """
    # Get active listings
    listings = SkinListing.objects.filter(status='ACTIVE').select_related('seller').order_by('-created_at')[:8]
    
    context = {
        'listings': listings,
    }
    return render(request, 'core/home.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def profile_settings(request):
    """
    Profile Settings view where users can update their Steam API key,
    trade URL, and wallet address.
    """
    if request.method == 'POST':
        user = request.user
        
        # Get form data
        steam_api_key = request.POST.get('steam_api_key', '').strip()
        trade_url = request.POST.get('trade_url', '').strip()
        wallet_address = request.POST.get('wallet_address', '').strip()
        
        # Validate and save
        errors = []
        
        if not steam_api_key:
            errors.append("Steam API Key is required.")
        if not trade_url:
            errors.append("Trade URL is required.")
        if not wallet_address:
            errors.append("Wallet Address is required.")
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Update user fields
            user.steam_api_key = steam_api_key
            user.trade_url = trade_url
            user.wallet_address = wallet_address
            user.save(update_fields=['steam_api_key', 'trade_url', 'wallet_address'])
            messages.success(request, "Profile settings saved successfully!")
            return redirect('core:profile_settings')
    
    # GET request - show form with current values
    context = {
        'user': request.user,
    }
    return render(request, 'core/profile_settings.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def sell_item(request):
    """
    Sell Item view - displays user's CS2 inventory and allows creating a listing.
    """
    user = request.user
    
    # Check if user has required settings
    if not user.steam_id:
        messages.error(request, "Please complete your Steam authentication first.")
        return redirect('core:profile_settings')
    
    if request.method == 'POST':
        # Handle item listing creation
        asset_id = request.POST.get('asset_id', '').strip()
        market_name = request.POST.get('market_name', '').strip()
        price_ton = request.POST.get('price_ton', '').strip()
        
        # Validate input
        errors = []
        
        if not asset_id:
            errors.append("Asset ID is required.")
        if not market_name:
            errors.append("Market name is required.")
        if not price_ton:
            errors.append("Price is required.")
        else:
            try:
                price_decimal = Decimal(price_ton)
                if price_decimal <= 0:
                    errors.append("Price must be greater than 0.")
            except (InvalidOperation, ValueError):
                errors.append("Invalid price format.")
        
        # Check if item is already listed
        existing_listing = SkinListing.objects.filter(
            seller=user,
            asset_id=asset_id,
            status='ACTIVE'
        ).first()
        
        if existing_listing:
            errors.append("This item is already listed for sale.")
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Create new listing
            try:
                listing = SkinListing.objects.create(
                    seller=user,
                    asset_id=asset_id,
                    market_name=market_name,
                    price_ton=price_decimal,
                    status='ACTIVE'
                )
                messages.success(request, f"Item '{market_name}' listed successfully for {price_ton} TON!")
                return redirect('core:my_listings')
            except Exception as e:
                messages.error(request, f"Error creating listing: {str(e)}")
    
    # GET request - fetch and display inventory
    inventory = []
    error_message = None
    
    # Check if user wants to force refresh the inventory
    force_refresh = request.GET.get('refresh', '').lower() == 'true'
    
    try:
        # Fetch inventory (uses caching to reduce API calls)
        inventory = get_user_inventory(user.steam_id, force_refresh=force_refresh)
        
        # Filter out items that are already listed
        active_listings = SkinListing.objects.filter(
            seller=user,
            status='ACTIVE'
        ).values_list('asset_id', flat=True)
        
        # Remove already listed items from inventory
        inventory = [item for item in inventory if item.get('asset_id') not in active_listings]
        
        if not inventory:
            messages.info(request, "No tradable items available to list, or all items are already listed.")
        elif force_refresh:
            messages.success(request, "Inventory refreshed successfully!")
    
    except ValueError as e:
        error_message = str(e)
        messages.error(request, error_message)
    except Exception as e:
        error_message = f"Failed to fetch inventory: {str(e)}"
        messages.error(request, error_message)
    
    context = {
        'inventory': inventory,
        'error_message': error_message,
        'user': user,
    }
    
    return render(request, 'core/sell_item.html', context)


@login_required
def deposit_funds(request):
    """
    Deposit Funds view - shows platform wallet address and user's unique comment code.
    """
    user = request.user
    
    # Get platform wallet address from settings
    platform_wallet = getattr(django_settings, 'PLATFORM_WALLET_ADDRESS', 'EQD...dummy_wallet_address_for_testing')
    
    # Get user's unique comment code
    comment_code = get_user_comment_code(user.id)
    
    # Get user's recent deposits
    recent_deposits = Deposit.objects.filter(user=user).order_by('-created_at')[:10]
    
    context = {
        'user': user,
        'platform_wallet': platform_wallet,
        'comment_code': comment_code,
        'recent_deposits': recent_deposits,
    }
    
    return render(request, 'core/deposit_funds.html', context)


from django.core.paginator import Paginator

@login_required
def browse_listings(request):
    """
    Browse all active listings.
    """
    listings_list = SkinListing.objects.filter(status='ACTIVE').select_related('seller').order_by('-created_at')
    
    # Optional: Add search/filter functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        listings_list = listings_list.filter(market_name__icontains=search_query)
        
    paginator = Paginator(listings_list, 12) # Show 12 listings per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'core/browse_listings.html', context)


@login_required
def listing_detail(request, listing_id):
    """
    View listing details and purchase option.
    """
    listing = get_object_or_404(SkinListing.objects.select_related('seller'), id=listing_id, status='ACTIVE')
    user = request.user
    
    # Check if user is trying to buy their own listing
    is_own_listing = listing.seller == user
    
    context = {
        'listing': listing,
        'is_own_listing': is_own_listing,
        'user': user,
    }
    return render(request, 'core/listing_detail.html', context)


@login_required
@require_http_methods(["POST"])
def purchase_listing(request, listing_id):
    """
    Purchase a listing - creates an order and freezes funds.
    """
    listing = get_object_or_404(SkinListing.objects.select_related('seller'), id=listing_id, status='ACTIVE')
    user = request.user
    
    # Validation
    if listing.seller == user:
        messages.error(request, "You cannot purchase your own listing.")
        return redirect('core:listing_detail', listing_id=listing_id)
    
    if user.balance_active < listing.price_ton:
        messages.error(request, f"Insufficient balance. You need {listing.price_ton} TON, but you have {user.balance_active} TON.")
        return redirect('core:deposit_funds')
    
    # Use atomic transaction
    try:
        with transaction.atomic():
            # Lock user and seller rows
            buyer = CustomUser.objects.select_for_update().get(id=user.id)
            seller = CustomUser.objects.select_for_update().get(id=listing.seller.id)
            listing_obj = SkinListing.objects.select_for_update().get(id=listing_id, status='ACTIVE')
            
            # Double-check balance
            if buyer.balance_active < listing_obj.price_ton:
                messages.error(request, "Insufficient balance. Please deposit more funds.")
                return redirect('core:deposit_funds')
            
            # Freeze buyer's funds
            buyer.balance_active -= listing_obj.price_ton
            buyer.balance_frozen += listing_obj.price_ton
            buyer.save(update_fields=['balance_active', 'balance_frozen'])
            
            # Create order
            order = Order.objects.create(
                buyer=buyer,
                seller=seller,
                listing=listing_obj,
                amount=listing_obj.price_ton,
                status='PAID'
            )
            
            # Mark listing as sold
            listing_obj.status = 'SOLD'
            listing_obj.save(update_fields=['status'])
            
            messages.success(request, f"Order created successfully! Order ID: #{order.id}")
            return redirect('core:order_detail', order_id=order.id)
    
    except Exception as e:
        messages.error(request, f"Error processing purchase: {str(e)}")
        return redirect('core:listing_detail', listing_id=listing_id)


@login_required
def my_listings(request):
    """
    View user's own listings.
    """
    user = request.user
    listings = SkinListing.objects.filter(seller=user).select_related('seller').order_by('-created_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status', '')
    if status_filter:
        listings = listings.filter(status=status_filter)
    
    context = {
        'listings': listings,
        'status_filter': status_filter,
    }
    return render(request, 'core/my_listings.html', context)


@login_required
@require_http_methods(["POST"])
def cancel_listing(request, listing_id):
    """
    Cancel a listing.
    """
    listing = get_object_or_404(SkinListing, id=listing_id, seller=request.user, status='ACTIVE')
    
    listing.status = 'CANCELLED'
    listing.save(update_fields=['status'])
    
    messages.success(request, "Listing cancelled successfully.")
    return redirect('core:my_listings')


@login_required
def my_orders(request):
    """
    View user's orders (as buyer and seller).
    """
    user = request.user
    
    # Get orders as buyer
    orders_as_buyer = Order.objects.filter(buyer=user).select_related('seller', 'listing').order_by('-created_at')
    
    # Get orders as seller
    orders_as_seller = Order.objects.filter(seller=user).select_related('buyer', 'listing').order_by('-created_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders_as_buyer = orders_as_buyer.filter(status=status_filter)
        orders_as_seller = orders_as_seller.filter(status=status_filter)
    
    context = {
        'orders_as_buyer': orders_as_buyer,
        'orders_as_seller': orders_as_seller,
        'status_filter': status_filter,
    }
    return render(request, 'core/my_orders.html', context)


@login_required
def order_detail(request, order_id):
    """
    View order details and handle status updates.
    """
    user = request.user
    order = get_object_or_404(
        Order.objects.select_related('buyer', 'seller', 'listing'),
        id=order_id
    )
    
    # Check if user is part of this order
    if order.buyer != user and order.seller != user:
        messages.error(request, "You don't have permission to view this order.")
        return redirect('core:my_orders')
    
    is_buyer = order.buyer == user
    is_seller = order.seller == user
    
    # Handle Status Updates
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if is_seller and action == 'mark_sent':
            if order.status == 'PAID':
                steam_trade_id = request.POST.get('steam_trade_id', '').strip()
                if steam_trade_id:
                    with transaction.atomic():
                        # Lock order row
                        order_obj = Order.objects.select_for_update().get(id=order.id)
                        if order_obj.status == 'PAID':
                            order_obj.status = 'SENT'
                            order_obj.steam_trade_id = steam_trade_id
                            order_obj.save(update_fields=['status', 'steam_trade_id'])
                            messages.success(request, "Order marked as sent. Waiting for buyer confirmation.")
                            return redirect('core:order_detail', order_id=order.id)
                else:
                    messages.error(request, "Please provide the Steam Trade ID.")
            else:
                 messages.error(request, "Invalid status for this action.")

        elif is_buyer and action == 'confirm_received':
            if order.status == 'SENT':
                with transaction.atomic():
                    # Lock rows
                    order_obj = Order.objects.select_for_update().get(id=order.id)
                    seller = CustomUser.objects.select_for_update().get(id=order.seller.id)
                    buyer = CustomUser.objects.select_for_update().get(id=order.buyer.id)
                    
                    if order_obj.status == 'SENT':
                        # Release funds
                        # Move from buyer frozen to seller active
                        # (Originally buyer active reduced, frozen increased. So now we reduce frozen and add to seller active)
                        
                        # Wait, in purchase_listing:
                        # buyer.balance_active -= price
                        # buyer.balance_frozen += price
                        
                        # So here:
                        buyer.balance_frozen -= order_obj.amount
                        seller.balance_active += order_obj.amount
                        
                        buyer.save(update_fields=['balance_frozen'])
                        seller.save(update_fields=['balance_active'])
                        
                        order_obj.status = 'COMPLETED'
                        order_obj.save(update_fields=['status'])
                        
                        messages.success(request, "Order completed! Funds released to seller.")
                        return redirect('core:order_detail', order_id=order.id)
            else:
                messages.error(request, "Invalid status for this action.")
                
    context = {
        'order': order,
        'is_buyer': is_buyer,
        'is_seller': is_seller,
    }
    return render(request, 'core/order_detail.html', context)


@login_required
def logout_view(request):
    """
    Logout the user and redirect to home page.
    """
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('core:home')

