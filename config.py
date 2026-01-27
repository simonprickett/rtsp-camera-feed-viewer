import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # Flask settings
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    PORT = int(os.getenv('FLASK_PORT', 5000))
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Camera configurations
    CAMERAS = {
        1: {
            'url': os.getenv('CAM_1', ''),
            'name': os.getenv('CAM_1_NAME', 'Camera 1')
        },
        2: {
            'url': os.getenv('CAM_2', ''),
            'name': os.getenv('CAM_2_NAME', 'Camera 2')
        },
        3: {
            'url': os.getenv('CAM_3', ''),
            'name': os.getenv('CAM_3_NAME', 'Camera 3')
        }
    }
    
    # Stream settings
    JPEG_QUALITY = int(os.getenv('JPEG_QUALITY', 80))
    RETRY_INTERVAL = int(os.getenv('RETRY_INTERVAL', 5))
    STREAM_TIMEOUT = int(os.getenv('STREAM_TIMEOUT', 10))
    
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
