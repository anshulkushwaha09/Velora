import os
import requests
import random
from dotenv import load_dotenv

load_dotenv()

class AssetManager:
    def __init__(self):
        self.pexels_key = os.getenv("PEXELS_API_KEY")
        self.pixabay_key = os.getenv("PIXABAY_API_KEY")
        
        if not self.pexels_key:
            raise EnvironmentError("PEXELS_API_KEY not set. Please add it to your .env file.")
        
        self.pexels_url = "https://api.pexels.com/videos/search"
        self.pixabay_url = "https://pixabay.com/api/videos/"
        
        # Ensure download directory exists
        self.assets_dir = os.path.join(os.getcwd(), "assets", "video_clips")
        os.makedirs(self.assets_dir, exist_ok=True)

    def _search_pexels(self, query):
        """Internal: Search Pexels specifically."""
        print(f"      📸 Searching Pexels...")
        headers = {"Authorization": self.pexels_key}
        params = {
            "query": query,
            "per_page": 5,
            "orientation": "portrait",
            "size": "medium"
        }
        try:
            r = requests.get(self.pexels_url, headers=headers, params=params, timeout=10)
            if r.status_code == 200:
                videos = r.json().get('videos', [])
                if videos:
                    # Pick best quality from a random choice of top 5
                    vid = random.choice(videos)
                    files = vid['video_files']
                    files.sort(key=lambda x: x['width'] * x['height'], reverse=True)
                    return files[0]['link']
        except: pass
        return None

    def _search_pixabay(self, query):
        """Internal: Search Pixabay specifically."""
        if not self.pixabay_key:
            return None
            
        print(f"      🎨 Searching Pixabay...")
        params = {
            "key": self.pixabay_key,
            "q": query,
            "per_page": 5,
            "video_type": "film", # 'film' or 'animation'
            "safesearch": "true"
        }
        try:
            r = requests.get(self.pixabay_url, params=params, timeout=10)
            if r.status_code == 200:
                hits = r.json().get('hits', [])
                if hits:
                    vid = random.choice(hits)
                    # Pixabay videos dict has 'large', 'medium', 'small', 'tiny'
                    # We want 'medium' or 'large'
                    v_data = vid['videos']
                    # Try large first, then medium
                    best = v_data.get('large', v_data.get('medium'))
                    return best['url']
        except: pass
        return None

    def search_video(self, query, duration_min=4):
        """
        Dual-Search Strategy:
        1. Try Pexels
        2. If fails, try Pixabay
        3. If fails, try simplified query on Pexels
        """
        print(f"   🔍 Searching for: '{query}'...")
        
        # Step 1: Pexels
        url = self._search_pexels(query)
        if url: return url

        # Step 2: Pixabay Fallback
        url = self._search_pixabay(query)
        if url: return url

        # Step 3: Simplified search
        if " " in query:
            simple = query.split()[-1]
            print(f"      ⚠️ No direct results. Trying simple: '{simple}'...")
            return self.search_video(simple)
            
        return None

    def download_video(self, url, filename):
        """
        Downloads the video content to a local file.
        """
        save_path = os.path.join(self.assets_dir, filename)
        
        # Caching strategy
        if os.path.exists(save_path):
            return save_path

        try:
            with requests.get(url, stream=True, timeout=15) as r:
                r.raise_for_status()
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            return save_path
        except Exception as e:
            print(f"      ❌ Error downloading {filename}: {e}")
            return None

    def get_videos(self, script_data):
        """
        NEW LOGIC: Downloads TWO videos per scene (A and B).
        Returns a list of tuples: [(path_a, path_b), (path_a, path_b), ...]
        """
        print("🎥 Starting Double-Feature Video Download...")
        video_pairs = []

        for scene in script_data:
            scene_id = scene['id']
            
            # 1. Get Search Terms
            # Fallback to 'keywords' if visual_1/2 don't exist (compatibility mode)
            query_a = scene.get('visual_1', scene.get('keywords', 'abstract'))
            query_b = scene.get('visual_2', query_a) # Use A if B is missing
            
            # 2. Search & Download Clip A
            url_a = self.search_video(query_a)
            path_a = None
            if url_a:
                path_a = self.download_video(url_a, f"scene_{scene_id}_a.mp4")
            
            # 3. Search & Download Clip B
            url_b = self.search_video(query_b)
            path_b = None
            if url_b:
                path_b = self.download_video(url_b, f"scene_{scene_id}_b.mp4")
            
            # 4. Fallback Logic (Self-Healing)
            # If B fails, use A twice. If A fails, use B twice.
            if not path_a and path_b: 
                path_a = path_b
                print(f"      ⚠️ Scene {scene_id} Clip A missing. Using Clip B for both.")
            if not path_b and path_a: 
                path_b = path_a
                print(f"      ⚠️ Scene {scene_id} Clip B missing. Using Clip A for both.")

            # 5. Final Check
            if path_a and path_b:
                video_pairs.append((path_a, path_b))
                print(f"   ✅ Scene {scene_id} Ready (A + B).")
            else:
                print(f"   ❌ Scene {scene_id} Completely Failed (No videos found).")
                video_pairs.append(None)

        return video_pairs

# --- TESTING ---
if __name__ == "__main__":
    manager = AssetManager()
    
    # Test with new dual-visual format
    test_script = [
        {
            "id": 1, 
            "visual_1": "cyberpunk city neon", 
            "visual_2": "hacker typing computer"
        }
    ]
    
    results = manager.get_videos(test_script)
    print("🎥 Assets Downloaded:", results)