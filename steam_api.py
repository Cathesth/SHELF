import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

def get_owned_games(steam_id: str):
    """
    Fetches the list of owned games for a given Steam ID.
    """
    api_key = os.getenv("STEAM_API_KEY")
    if not api_key:
        # Try to fail gracefully or return None so the UI can handle it
        print("STEAM_API_KEY is not set.")
        return None

    url = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
    params = {
        "key": api_key,
        "steamid": steam_id,
        "format": "json",
        "include_appinfo": "1",  # Include game name and logo
        "include_played_free_games": "1"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "response" in data and "games" in data["response"]:
            return data["response"]["games"]
        else:
            return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching games: {e}")
        return None

def get_game_details(app_id: int):
    """
    Fetches details for a specific game from the Steam Store API.
    Note: strict rate limits apply.
    """
    url = "https://store.steampowered.com/api/appdetails"
    params = {
        "appids": app_id,
        "l": "koreana" # Request Korean data if available
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 429:
            print("Rate limit exceeded for Store API")
            time.sleep(2) # Simple backoff
            return None
            
        data = response.json()
        if data and str(app_id) in data and data[str(app_id)]["success"]:
            return data[str(app_id)]["data"]
        return None
    except Exception as e:
        print(f"Error fetching details for app {app_id}: {e}")
        return None
