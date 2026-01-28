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
    Query params:
        motion: Enable motion detection ('true' or 'false')
    """
    from flask import request

    # Validate camera_id
    if camera_id not in Config.CAMERAS:
        logger.error(f"Invalid camera ID: {camera_id}")
        return "Invalid camera ID", 404

    # Validate quality
    if quality not in ['main', 'sub']:
        logger.error(f"Invalid quality: {quality}")
        return "Invalid quality parameter", 400

    # Get motion detection parameter from query string
    enable_motion = request.args.get('motion', 'false').lower() == 'true'

    # Get camera URL for specified quality
    rtsp_url = Config.get_camera_url(camera_id, quality)

    if not rtsp_url:
        logger.error(f"No URL configured for camera {camera_id}")
        return "Camera not configured", 404

    # Create unique key for this stream (do NOT include motion state to reuse handler)
    stream_key = f"{camera_id}_{quality}"

    # Create or reuse stream handler
    if stream_key not in stream_handlers:
        logger.info(f"Creating new stream handler for camera {camera_id} ({quality})")
        stream_handlers[stream_key] = StreamHandler(
            rtsp_url,
            jpeg_quality=Config.JPEG_QUALITY,
            timeout=Config.STREAM_TIMEOUT,
            retry_interval=Config.RETRY_INTERVAL,
            enable_motion_detection=enable_motion,
            motion_sensitivity=Config.MOTION_SENSITIVITY,
            motion_min_area=Config.MOTION_MIN_AREA
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
                retry_interval=Config.RETRY_INTERVAL,
                enable_motion_detection=enable_motion,
                motion_sensitivity=Config.MOTION_SENSITIVITY,
                motion_min_area=Config.MOTION_MIN_AREA
            )
        else:
            # Just update motion detection state on existing handler
            logger.info(f"Toggling motion detection for camera {camera_id} to {enable_motion}")
            stream_handlers[stream_key].set_motion_detection(enable_motion)

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


@app.route('/api/motion/<int:camera_id>/<quality>')
def get_motion_status(camera_id, quality):
    """API endpoint to check motion detection status"""
    if camera_id not in Config.CAMERAS:
        return jsonify({'error': 'Invalid camera ID'}), 404

    # Use same stream key as video_feed (without motion state)
    stream_key = f"{camera_id}_{quality}"

    if stream_key in stream_handlers:
        handler = stream_handlers[stream_key]
        return jsonify({
            'camera_id': camera_id,
            'quality': quality,
            'motion_enabled': handler.motion_detector.enabled,
            'motion_detected': handler.is_motion_detected()
        })

    # No active stream
    return jsonify({
        'camera_id': camera_id,
        'quality': quality,
        'motion_enabled': False,
        'motion_detected': False
    })


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
