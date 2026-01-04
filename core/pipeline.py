"""
Social auth pipeline functions for Steam authentication.
"""


def save_steam_id(strategy, details, backend, user=None, *args, **kwargs):
    """
    Pipeline function to save Steam ID to CustomUser model.
    Steam OpenID returns the Steam ID in the response.
    """
    if backend.name == 'steam' and user:
        response = kwargs.get('response', {})
        
        # Steam ID can be in different places depending on the response
        steam_id = None
        if isinstance(response, dict):
            steam_id = response.get('steamid') or response.get('personaname')
        
        if not steam_id:
            steam_id = kwargs.get('uid')
        
        # If uid is a URL, extract the Steam ID from it
        if not steam_id and kwargs.get('uid'):
            uid = kwargs['uid']
            if isinstance(uid, str) and 'steamcommunity.com' in uid:
                steam_id = uid.split('/')[-1]
            else:
                steam_id = str(uid)
        
        # Also check username field which might contain Steam ID
        if not steam_id and kwargs.get('username'):
            username = kwargs['username']
            if isinstance(username, str) and 'steamcommunity.com' in username:
                steam_id = username.split('/')[-1]
            elif username.isdigit():
                steam_id = username
        
        if steam_id:
            # Ensure it's a string and clean it
            steam_id = str(steam_id).strip()
            if steam_id and not user.steam_id:
                user.steam_id = steam_id
                user.save(update_fields=['steam_id'])
    
    return {'user': user}
