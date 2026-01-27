"""
Flask RTSP Camera Viewer Application
"""
from flask import Flask, render_template, Response, jsonify
import logging
from config import Config
from utils.stream_handler import StreamHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Load camera configurations from JSON
if not Config.load_cameras():
    logger.warning("Failed to load camera configurations")

# Store active stream handlers
stream_handlers = {}


@app.route('/')
def index():
    """Main page displaying all camera streams"""
    cameras = []
    for camera_id in sorted(Config.CAMERAS.keys()):
        camera_info = {
            'id': camera_id,
            'name': Config.get_camera_name(camera_id),
            'url': Config.get_camera_url(camera_id)
        }
        cameras.append(camera_info)
    
    return render_template('index.html', cameras=cameras)


@app.route('/stream/<int:camera_id>/<quality>')
def video_feed(camera_id, quality):
    """
    Video streaming route for specified camera and quality
    
    Args:
        camera_id: Camera ID (1, 2, or 3)
        quality: Stream quality ('main' for ch0, 'sub' for ch1)
    """
    # Validate camera_id
    if camera_id not in Config.CAMERAS:
        logger.error(f"Invalid camera ID: {camera_id}")
        return "Invalid camera ID", 404
    
    # Validate quality
    if quality not in ['main', 'sub']:
        logger.error(f"Invalid quality: {quality}")
        return "Invalid quality parameter", 400
    
    # Get camera URL for specified quality
    rtsp_url = Config.get_camera_url(camera_id, quality)
    
    if not rtsp_url:
        logger.error(f"No URL configured for camera {camera_id}")
        return "Camera not configured", 404
    
    # Create unique key for this stream
    stream_key = f"{camera_id}_{quality}"
    
    # Create or reuse stream handler
    if stream_key not in stream_handlers:
        logger.info(f"Creating new stream handler for camera {camera_id} ({quality})")
        stream_handlers[stream_key] = StreamHandler(
            rtsp_url,
            jpeg_quality=Config.JPEG_QUALITY,
            timeout=Config.STREAM_TIMEOUT,
            retry_interval=Config.RETRY_INTERVAL
        )
    else:
        # Check if URL changed (in case of quality toggle)
        current_url = stream_handlers[stream_key].rtsp_url
        if current_url != rtsp_url:
            logger.info(f"URL changed for camera {camera_id}, recreating handler")
            stream_handlers[stream_key].cleanup()
            stream_handlers[stream_key] = StreamHandler(
                rtsp_url,
                jpeg_quality=Config.JPEG_QUALITY,
                timeout=Config.STREAM_TIMEOUT,
                retry_interval=Config.RETRY_INTERVAL
            )
    
    return Response(
        stream_handlers[stream_key].generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/api/cameras')
def get_cameras():
    """API endpoint to get camera information"""
    cameras = []
    for camera_id in sorted(Config.CAMERAS.keys()):
        camera_info = {
            'id': camera_id,
            'name': Config.get_camera_name(camera_id),
            'has_url': bool(Config.get_camera_url(camera_id))
        }
        cameras.append(camera_info)
    
    return jsonify(cameras)


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})


def cleanup():
    """Cleanup all stream handlers"""
    logger.info("Cleaning up stream handlers...")
    for handler in stream_handlers.values():
        handler.cleanup()
    stream_handlers.clear()


if __name__ == '__main__':
    try:
        logger.info(f"Starting Flask app on port {Config.PORT}")
        logger.info(f"Debug mode: {Config.DEBUG}")
        app.run(
            host='0.0.0.0',
            port=Config.PORT,
            debug=Config.DEBUG,
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        cleanup()
    except Exception as e:
        logger.error(f"Error starting app: {e}")
        cleanup()
