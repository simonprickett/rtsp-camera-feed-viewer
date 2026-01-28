import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # Flask settings
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    PORT = int(os.getenv('FLASK_PORT', 5000))
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Camera configurations - loaded from JSON file
    CAMERAS = {}
    
    @staticmethod
    def load_cameras():
        """Load camera configurations from cameras.json"""
        try:
            cameras_file = os.path.join(os.path.dirname(__file__), 'cameras.json')
            with open(cameras_file, 'r') as f:
                cameras_list = json.load(f)
            
            # Convert list to dictionary keyed by camera ID
            Config.CAMERAS = {}
            for camera in cameras_list:
                if camera.get('enabled', True):  # Only load enabled cameras
                    camera_id = camera['id']
                    Config.CAMERAS[camera_id] = {
                        'url': camera['url'],
                        'name': camera['name']
                    }
            
            return True
        except FileNotFoundError:
            print("Warning: cameras.json not found. No cameras configured.")
            return False
        except json.JSONDecodeError as e:
            print(f"Error parsing cameras.json: {e}")
            return False
        except Exception as e:
            print(f"Error loading cameras: {e}")
            return False
    
    # Stream settings
    JPEG_QUALITY = int(os.getenv('JPEG_QUALITY', 80))
    RETRY_INTERVAL = int(os.getenv('RETRY_INTERVAL', 5))
    STREAM_TIMEOUT = int(os.getenv('STREAM_TIMEOUT', 10))

    # Motion detection settings
    MOTION_DETECTION_ENABLED = os.getenv('MOTION_DETECTION_ENABLED', 'False').lower() == 'true'
    MOTION_SENSITIVITY = os.getenv('MOTION_SENSITIVITY', 'medium')  # low, medium, high
    MOTION_MIN_AREA = int(os.getenv('MOTION_MIN_AREA', 500))  # Minimum contour area in pixels

    @staticmethod
    def get_camera_url(camera_id, quality='main'):
        """Get camera URL with specified quality (main=ch0, sub=ch1)"""
        if camera_id not in Config.CAMERAS:
            return None
        
        base_url = Config.CAMERAS[camera_id]['url']
        if not base_url:
            return None
        
        # Replace channel in URL
        if quality == 'sub':
            # Replace /ch0 with /ch1
            if '/ch0' in base_url:
                return base_url.replace('/ch0', '/ch1')
            # If no channel specified, try to add /ch1
            elif base_url.endswith(('554', '554/')):
                return base_url.rstrip('/') + '/ch1'
        else:  # main quality
            # Replace /ch1 with /ch0
            if '/ch1' in base_url:
                return base_url.replace('/ch1', '/ch0')
            # If no channel specified, keep as is (usually defaults to main)
        
        return base_url
    
    @staticmethod
    def get_camera_name(camera_id):
        """Get camera display name"""
        if camera_id not in Config.CAMERAS:
            return f'Camera {camera_id}'
        return Config.CAMERAS[camera_id]['name']
