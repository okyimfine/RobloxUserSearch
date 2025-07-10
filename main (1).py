
from flask import Flask, render_template, request, jsonify
import requests
import json
from datetime import datetime
import time
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

class RobloxSearchAPI:
    def __init__(self):
        self.base_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty'
        }

    def make_request(self, url, method='GET', json_data=None, max_retries=3):
        """Make HTTP request with retry logic"""
        for attempt in range(max_retries):
            try:
                session = requests.Session()
                session.headers.update(self.base_headers)
                
                if method == 'POST':
                    response = session.post(url, json=json_data, timeout=15)
                else:
                    response = session.get(url, timeout=15)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    # Rate limited, wait and retry
                    time.sleep(2 ** attempt)
                    continue
                else:
                    return None
                    
            except requests.exceptions.RequestException:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return None
        return None

    def get_user_id_by_username(self, username):
        """Get user ID by username using multiple methods"""
        # Method 1: Try the usernames endpoint
        try:
            url = "https://users.roblox.com/v1/usernames/users"
            data = {"usernames": [username], "excludeBannedUsers": True}
            result = self.make_request(url, method='POST', json_data=data)
            
            if result and result.get("data") and len(result["data"]) > 0:
                return result["data"][0].get("id")
        except:
            pass
        
        # Method 2: Try the search endpoint
        try:
            url = f"https://users.roblox.com/v1/users/search?keyword={username}&limit=10"
            result = self.make_request(url)
            
            if result and result.get("data"):
                for user in result["data"]:
                    if user.get("name", "").lower() == username.lower():
                        return user.get("id")
        except:
            pass
        
        return None

    def get_roblox_user_info(self, username: str):
        """Get comprehensive Roblox user information"""
        try:
            # Get user ID
            user_id = self.get_user_id_by_username(username)
            
            if not user_id:
                return {"found": False, "error": "User not found"}

            # Get basic user info
            user_info_url = f"https://users.roblox.com/v1/users/{user_id}"
            user_info = self.make_request(user_info_url)
            
            if not user_info:
                return {"found": False, "error": "Could not fetch user information"}

            # Get avatar image
            avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=420x420&format=Png&isCircular=false"
            avatar_data = self.make_request(avatar_url)
            avatar_image_url = None
            
            if avatar_data and avatar_data.get("data") and len(avatar_data["data"]) > 0:
                avatar_image_url = avatar_data["data"][0].get("imageUrl")

            # Get user presence (online status)
            presence_url = "https://presence.roblox.com/v1/presence/users"
            presence_data = {"userIds": [user_id]}
            presence_info = self.make_request(presence_url, method='POST', json_data=presence_data)

            online_status = "Offline"
            last_location = "Unknown"
            current_game = "Not playing"
            is_actually_playing = False

            if presence_info and presence_info.get("userPresences"):
                for presence in presence_info["userPresences"]:
                    if presence.get("userId") == user_id:
                        status_type = presence.get("userPresenceType", 0)
                        if status_type == 0:
                            online_status = "Offline"
                        elif status_type == 1:
                            online_status = "Online"
                        elif status_type == 2:
                            online_status = "InGame"
                            is_actually_playing = True
                        elif status_type == 3:
                            online_status = "InStudio"
                        
                        last_location = presence.get("lastLocation", "Unknown")
                        
                        # Get game info if playing
                        if status_type == 2:  # InGame
                            universe_id = presence.get("universeId")
                            place_id = presence.get("placeId")
                            
                            if universe_id:
                                game_url = f"https://games.roblox.com/v1/games?universeIds={universe_id}"
                                game_data = self.make_request(game_url)
                                if game_data and game_data.get("data") and len(game_data["data"]) > 0:
                                    current_game = game_data["data"][0].get("name", "Unknown Game")
                            
                            if current_game == "Not playing" and place_id:
                                current_game = "Playing a game"
                        
                        break

            # Get social stats
            friends_count = "0"
            followers_count = "0"
            following_count = "0"

            # Friends count
            friends_url = f"https://friends.roblox.com/v1/users/{user_id}/friends/count"
            friends_data = self.make_request(friends_url)
            if friends_data and "count" in friends_data:
                friends_count = friends_data["count"]

            # Followers count
            followers_url = f"https://friends.roblox.com/v1/users/{user_id}/followers/count"
            followers_data = self.make_request(followers_url)
            if followers_data and "count" in followers_data:
                followers_count = followers_data["count"]

            # Following count
            following_url = f"https://friends.roblox.com/v1/users/{user_id}/followings/count"
            following_data = self.make_request(following_url)
            if following_data and "count" in following_data:
                following_count = following_data["count"]

            return {
                "found": True,
                "id": user_id,
                "username": user_info.get("name", username),
                "display_name": user_info.get("displayName", username),
                "description": user_info.get("description", "No description"),
                "created": user_info.get("created", "Unknown"),
                "is_banned": user_info.get("isBanned", False),
                "online_status": online_status,
                "last_location": last_location,
                "current_game": current_game,
                "is_actually_playing": is_actually_playing,
                "friends_count": friends_count,
                "followers_count": followers_count,
                "following_count": following_count,
                "avatar_url": avatar_image_url,
                "search_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        except Exception as e:
            return {"found": False, "error": f"Service temporarily unavailable. Please try again."}

# Initialize the API
roblox_api = RobloxSearchAPI()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search_user():
    try:
        data = request.get_json()
        username = data.get('username', '').strip()

        if not username:
            return jsonify({"error": "Username is required"}), 400

        if len(username) > 20:
            return jsonify({"error": "Username too long"}), 400

        if not username.replace('_', '').isalnum():
            return jsonify({"error": "Invalid username format"}), 400

        result = roblox_api.get_roblox_user_info(username)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"found": False, "error": "Search failed. Please try again."}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
