"""
Steam service for fetching user inventory and CS2 items.
Clean implementation with proper caching and 429 handling.
"""
import requests
import time
from typing import List, Dict, Optional
from django.core.cache import cache
from django.conf import settings

# Cache timeout: 10 minutes
CACHE_TIMEOUT = 600


def get_user_inventory(steam_id: str, force_refresh: bool = False) -> List[Dict]:
    """
    Fetch CS2 inventory for a given Steam ID.
    Uses caching to prevent 429 errors.
    
    Args:
        steam_id: Steam ID of the user
        force_refresh: If True, bypass cache and fetch fresh data
    
    Returns:
        List of tradable CS2 items with their details
    """
    if not steam_id:
        raise ValueError("Steam ID is required")
    
    # Check cache first (unless force refresh)
    cache_key = f"inventory_{steam_id}"
    
    if not force_refresh:
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data
    
    # Fetch from Steam Community API
    url = f"https://steamcommunity.com/inventory/{steam_id}/730/2"
    params = {
        'l': 'english',
        'count': 5000
    }
    
    # MUST include User-Agent or Steam will block the request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # Try twice with simple retry logic
    for attempt in range(2):
        try:
            print(f"[DEBUG] Attempt {attempt + 1}: Fetching inventory for {steam_id}")
            response = requests.get(url, params=params, headers=headers, timeout=10)
            print(f"[DEBUG] Response status: {response.status_code}")
            
            # Handle 429 Rate Limit
            if response.status_code == 429:
                print(f"[DEBUG] 429 Rate Limited on attempt {attempt + 1}")
                if attempt == 0:
                    # First attempt failed, wait 2 seconds and try once more
                    time.sleep(2)
                    continue
                else:
                    # Second attempt also failed
                    raise Exception("Steam is busy right now. Please try again in a moment.")
            
            # Handle 403 Private Inventory
            if response.status_code == 403:
                print(f"[DEBUG] 403 Private Inventory")
                raise Exception("Your Steam inventory is private. Please set it to public in your Steam privacy settings.")
            
            # Handle other errors
            if response.status_code != 200:
                print(f"[DEBUG] Unexpected status code: {response.status_code}")
                raise Exception(f"Steam returned error {response.status_code}")
            
            # Parse the JSON response
            data = response.json()
            print(f"[DEBUG] JSON parsed successfully")
            print(f"[DEBUG] Has 'assets': {'assets' in data}, Has 'descriptions': {'descriptions' in data}")
            
            if not data or 'assets' not in data or 'descriptions' not in data:
                print(f"[DEBUG] Empty or invalid data structure")
                return []
            
            # Map descriptions by classid for easy lookup
            descriptions_map = {}
            for desc in data.get('descriptions', []):
                classid = str(desc.get('classid'))
                descriptions_map[classid] = desc
            
            print(f"[DEBUG] Total descriptions: {len(descriptions_map)}")
            print(f"[DEBUG] Total assets: {len(data.get('assets', []))}")
            
            # Process items
            inventory = []
            tradable_count = 0
            for asset in data.get('assets', []):
                classid = str(asset.get('classid'))
                description = descriptions_map.get(classid)
                
                # Only include tradable items
                if description and description.get('tradable') == 1:
                    tradable_count += 1
                    # Get market name
                    market_name = description.get('market_hash_name', 'Unknown Item')
                    
                    # Build full image URL
                    icon_hash = description.get('icon_url', '')
                    icon_url = f"https://community.cloudflare.steamstatic.com/economy/image/{icon_hash}" if icon_hash else ''
                    
                    inventory.append({
                        'asset_id': asset.get('assetid', ''),
                        'class_id': classid,
                        'instance_id': str(asset.get('instanceid', '0')),
                        'market_name': market_name,
                        'market_hash_name': market_name,
                        'icon_url': icon_url,
                        'icon_url_large': icon_url,
                        'tradable': 1,
                        'marketable': description.get('marketable', 0),
                        'type': description.get('type', ''),
                        'name': market_name,
                        'descriptions': description.get('descriptions', []),
                        'tags': description.get('tags', []),
                    })
            
            print(f"[DEBUG] Tradable items found: {tradable_count}")
            print(f"[DEBUG] Final inventory count: {len(inventory)}")
            
            # Cache the result for 10 minutes
            cache.set(cache_key, inventory, CACHE_TIMEOUT)
            print(f"[DEBUG] Inventory cached successfully")
            
            return inventory
            
        except requests.exceptions.RequestException as e:
            if attempt == 0:
                time.sleep(2)
                continue
            raise Exception(f"Failed to connect to Steam: {str(e)}")
    
    # Should never reach here, but just in case
    raise Exception("Failed to fetch inventory after retries")


def invalidate_inventory_cache(steam_id: str) -> None:
    """
    Clear cached inventory for a specific user.
    """
    cache_key = f"inventory_{steam_id}"
    cache.delete(cache_key)


def get_item_details(asset_id: str, steam_id: str) -> Optional[Dict]:
    """
    Get details for a specific item from the user's inventory.
    """
    inventory = get_user_inventory(steam_id)
    
    for item in inventory:
        if item.get('asset_id') == asset_id:
            return item
    
    return None
