import os
import requests
import random
from typing import List, Dict

class AssetManager:
    def __init__(self, pexels_api_key="", pixabay_api_key=""):
        # Load API keys from environment if not provided
        self.pexels_key = pexels_api_key or os.getenv("PEXELS_API_KEY", "")
        self.pixabay_key = pixabay_api_key or os.getenv("PIXABAY_API_KEY", "")
        
        # Directories
        self.assets_dir = os.path.join(os.getcwd(), "assets", "video_clips")
        os.makedirs(self.assets_dir, exist_ok=True)

    def download_video(self, url: str, filename: str) -> str:
        """
        Downloads a video with retries and a headers fake-out.
        """
        save_path = os.path.join(self.assets_dir, filename)
        
        # Caching strategy (ensure file exists AND is not empty)
        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            return save_path

        try:
            print(f"      📥 Downloading clip to: {filename}...")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return save_path

        except Exception as e:
            print(f"      ⚠️ Download failed: {e}")
            if os.path.exists(save_path):
                os.remove(save_path)
            return None

    def search_pexels(self, query: str) -> str:
        """
        Search Pexels API for a 1080x1920 (Portrait) video.
        """
        if not self.pexels_key:
            return None
            
        url = "https://api.pexels.com/videos/search"
        headers = {"Authorization": self.pexels_key}
        params = {
            "query": query,
            "orientation": "portrait",
            "per_page": 5,
            "min_width": 720
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            videos = data.get("videos", [])
            if not videos:
                return None
                
            # Pick a random one for variety or use the first
            video = random.choice(videos)
            
            # Find the best quality link
            files = video.get("video_files", [])
            # Priority: 1080x1920 or highest res
            files.sort(key=lambda x: x.get("width", 0), reverse=True)
            
            return files[0].get("link")
        except Exception as e:
            print(f"      ⚠️ Pexels Error: {e}")
            return None

    def search_pixabay(self, query: str) -> str:
        """
        Search Pixabay API for a video.
        """
        if not self.pixabay_key:
            return None
            
        url = "https://pixabay.com/api/videos/"
        params = {
            "key": self.pixabay_key,
            "q": query,
            "per_page": 5,
            "video_type": "film"
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            hits = data.get("hits", [])
            if not hits:
                return None
                
            video = random.choice(hits)
            # Pixabay provides fixed sizes: large, medium, small
            return video.get("videos", {}).get("medium", {}).get("url")
        except Exception as e:
            print(f"      ⚠️ Pixabay Error: {e}")
            return None

    def get_videos(self, script_data: List[Dict]) -> Dict:
        """
        Downloads two clips per scene for the A/B transition logic.
        v9.0 Update: Uses 'visual_search_1' and 'visual_search_2'.
        """
        print(f"🎞️ Gathering Visual Assets for {len(script_data)} scenes...")
        assets_map = {}
        
        for scene in script_data:
            scene_id = scene['id']
            # Support both legacy (visual_1) and new v9.0 schema
            q1 = scene.get('visual_search_1', scene.get('visual_1', 'mystery'))
            q2 = scene.get('visual_search_2', scene.get('visual_2', 'ancient history'))
            
            print(f"   🔍 Scene {scene_id}: Searching for '{q1}' & '{q2}'...")
            
            path_a = None
            path_b = None
            
            # Clip A: Search Pexels then Pixabay
            link_a = self.search_pexels(q1) or self.search_pixabay(q1)
            if link_a:
                path_a = self.download_video(link_a, f"scene_{scene_id}_a.mp4")
            
            # Clip B: Search Pexels then Pixabay
            link_b = self.search_pexels(q2) or self.search_pixabay(q2)
            if link_b:
                path_b = self.download_video(link_b, f"scene_{scene_id}_b.mp4")
                
            # Fallbacks: If one failed, duplicate the other for stitching safety
            if path_a and not path_b:
                path_b = path_a
            if path_b and not path_a:
                path_a = path_b
                
            if path_a and path_b:
                assets_map[scene_id] = (path_a, path_b)
                print(f"   ✅ Scene {scene_id} Ready (A + B).")
            else:
                print(f"   ❌ Scene {scene_id} Completely Failed (No videos found).")
                assets_map[scene_id] = None
        
        return assets_map