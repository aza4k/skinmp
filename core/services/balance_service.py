"""
Balance service for handling deposits and balance operations.
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from core.models import CustomUser, Deposit


def process_deposit(user_id: int, amount: Decimal, tx_hash: str, comment_code: str = None) -> Deposit:
    """
    Process a deposit transaction and add funds to user's active balance.
    
    This function uses database transactions to ensure atomicity and prevent
    race conditions when updating user balances.
    
    Args:
        user_id: ID of the user making the deposit
        amount: Amount to deposit (must be positive)
        tx_hash: Blockchain transaction hash (must be unique)
        comment_code: Optional comment code used for deposit identification
    
    Returns:
        Deposit object that was created/updated
    
    Raises:
        ValidationError: If validation fails (negative amount, duplicate tx_hash, etc.)
        CustomUser.DoesNotExist: If user doesn't exist
    """
    if amount <= 0:
        raise ValidationError("Deposit amount must be greater than zero.")
    
    if not tx_hash or not tx_hash.strip():
        raise ValidationError("Transaction hash is required.")
    
    # Use atomic transaction to ensure data consistency
    with transaction.atomic():
        # Get user and lock the row for update to prevent race conditions
        try:
            user = CustomUser.objects.select_for_update().get(id=user_id)
        except CustomUser.DoesNotExist:
            raise CustomUser.DoesNotExist(f"User with ID {user_id} does not exist.")
        
        # Check if transaction hash already exists
        existing_deposit = Deposit.objects.filter(tx_hash=tx_hash).first()
        if existing_deposit:
            raise ValidationError(f"Transaction hash {tx_hash} already exists. This deposit may have already been processed.")
        
        # Generate comment code if not provided
        if not comment_code:
            comment_code = f"user_{user_id}"
        
        # Create deposit record
        deposit = Deposit.objects.create(
            user=user,
            amount=amount,
            tx_hash=tx_hash,
            comment_code=comment_code,
            status='PENDING'
        )
        
        # Update user's active balance
        user.balance_active += amount
        user.save(update_fields=['balance_active'])
        
        # Update deposit status to confirmed
        deposit.status = 'CONFIRMED'
        deposit.confirmed_at = timezone.now()
        deposit.save(update_fields=['status', 'confirmed_at'])
        
        return deposit


def get_user_comment_code(user_id: int) -> str:
    """
    Get the unique comment code for a user.
    
    Args:
        user_id: ID of the user
    
    Returns:
        Comment code string (e.g., "user_123")
    """
    return f"user_{user_id}"
