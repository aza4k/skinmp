"""
Steam service for fetching user inventory.
Uses Direct Steam API with STRICT caching to prevent rate limits.
"""
import requests
import time
from typing import List, Dict, Optional
from django.core.cache import cache
from django.conf import settings

# Cache timeout: 24 hours
# We rely on this heavily. 
# API is ONLY called if user explicitly clicks "Refresh" OR cache is empty.
CACHE_TIMEOUT = 86400

def get_user_inventory(steam_id: str, force_refresh: bool = False) -> List[Dict]:
    """
    Fetch CS2 inventory from Steam Community API.
    
    STRICT CACHING POLICY:
    - If force_refresh is False: ALWAYS return cached data if exists.
    - If force_refresh is True: Call Steam API, update cache.
    """
    # 1. Validation
    if not steam_id:
        raise ValueError("Steam ID is required")
    
    steam_id = str(steam_id).strip()
    if not steam_id.isdigit():
        raise ValueError(f"Invalid Steam ID format: {steam_id}")
    
    # 2. STRICT CACHE CHECK (F5 Protection)
    cache_key = f"inventory_{steam_id}"
    
    if not force_refresh:
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            print(f"[DEBUG] Returning cached inventory for {steam_id} (No API Call)")
            return cached_data
    
    # 3. Direct Steam API Call
    # Only reaches here if cache is empty OR force_refresh=True
    url = f"https://steamcommunity.com/inventory/{steam_id}/730/2"
    params = {'l': 'english', 'count': 5000}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print(f"[Prod Debug] Fetching from Direct Steam API: {url}")
    
    # Retry logic for 429 (Rate Limit)
    for attempt in range(2):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 429:
                print(f"[DEBUG] 429 Rate Limit hit.")
                if attempt == 0:
                    time.sleep(2)
                    continue
                else:
                    # If we fail and have old cache, maybe return it? 
                    # But force_refresh was requested...
                    raise Exception("Steam is rate-limiting requests. Please wait a few minutes.")
            
            if response.status_code == 403:
                raise Exception("Inventory is Private. Set to Public.")
                
            if response.status_code != 200:
                raise Exception(f"Steam Error {response.status_code}")
                
            data = response.json()
            if not data or 'assets' not in data:
                 return [] # Empty inventory
            
            # 4. Parse (Old simplified logic)
            descriptions_map = {}
            for desc in data.get('descriptions', []):
                descriptions_map[str(desc.get('classid'))] = desc
            
            inventory = []
            for asset in data.get('assets', []):
                classid = str(asset.get('classid'))
                description = descriptions_map.get(classid)
                
                if description and description.get('tradable') == 1:
                    market_name = description.get('market_hash_name', 'Unknown')
                    icon_hash = description.get('icon_url', '')
                    icon_url = f"https://community.cloudflare.steamstatic.com/economy/image/{icon_hash}" if icon_hash else ''
                    
                    inventory.append({
                        'asset_id': asset.get('assetid'),
                        'market_name': market_name,
                        'market_hash_name': market_name,
                        'icon_url': icon_url,
                        'tradable': 1
                    })
            
            # 5. Update Cache
            print(f"[DEBUG] Caching {len(inventory)} items.")
            cache.set(cache_key, inventory, CACHE_TIMEOUT)
            return inventory
            
        except requests.exceptions.RequestException as e:
            if attempt == 0:
                time.sleep(2)
                continue
            raise Exception(f"Connection Error: {e}")

    return []

def get_item_details(asset_id: str, steam_id: str) -> Optional[Dict]:
    # Reuse main function, logic ensures we use cache if available
    inventory = get_user_inventory(steam_id, force_refresh=False)
    for item in inventory:
        if item.get('asset_id') == asset_id:
            return item
    return None
