"""
Stream handler for RTSP to MJPEG conversion
"""
import cv2
import time
import logging
from threading import Lock

logger = logging.getLogger(__name__)


class StreamHandler:
    """Handle RTSP stream capture and MJPEG conversion"""
    
    def __init__(self, rtsp_url, jpeg_quality=80, timeout=10, retry_interval=5):
        self.rtsp_url = rtsp_url
        self.jpeg_quality = jpeg_quality
        self.timeout = timeout
        self.retry_interval = retry_interval
        self.cap = None
        self.lock = Lock()
        self.consecutive_failures = 0
        self.max_failures = 3
        
    def connect(self):
        """Initialize video capture connection"""
        try:
            if self.cap is not None:
                self.cap.release()
            
            logger.info(f"Connecting to RTSP stream: {self._sanitize_url(self.rtsp_url)}")
            self.cap = cv2.VideoCapture(self.rtsp_url)
            
            # Set buffer size to reduce latency
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Set timeout (in milliseconds)
            self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, self.timeout * 1000)
            
            if not self.cap.isOpened():
                logger.error(f"Failed to open stream: {self._sanitize_url(self.rtsp_url)}")
                return False
            
            logger.info(f"Successfully connected to: {self._sanitize_url(self.rtsp_url)}")
            self.consecutive_failures = 0
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to stream: {e}")
            return False
    
    def _sanitize_url(self, url):
        """Remove credentials from URL for logging"""
        try:
            if '@' in url:
                # Extract everything after @
                return url.split('@', 1)[1]
            return url
        except:
            return "unknown"
    
    def generate_frames(self):
        """Generate MJPEG frames from RTSP stream"""
        last_reconnect_attempt = 0
        
        while True:
            with self.lock:
                # Try to connect if not connected
                if self.cap is None or not self.cap.isOpened():
                    current_time = time.time()
                    if current_time - last_reconnect_attempt >= self.retry_interval:
                        self.connect()
                        last_reconnect_attempt = current_time
                    
                    if self.cap is None or not self.cap.isOpened():
                        # Return a black frame when disconnected
                        yield self._generate_error_frame("Connecting...")
                        time.sleep(0.5)
                        continue
                
                try:
                    success, frame = self.cap.read()
                    
                    if not success or frame is None:
                        self.consecutive_failures += 1
                        logger.warning(f"Failed to read frame (failure {self.consecutive_failures}/{self.max_failures})")
                        
                        if self.consecutive_failures >= self.max_failures:
                            logger.error("Max consecutive failures reached, reconnecting...")
                            if self.cap is not None:
                                self.cap.release()
                                self.cap = None
                            yield self._generate_error_frame("Connection lost")
                            time.sleep(0.5)
                            continue
                        
                        # Wait a bit before next attempt
                        time.sleep(0.1)
                        continue
                    
                    # Reset failure counter on success
                    self.consecutive_failures = 0
                    
                    # Encode frame as JPEG
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
                    ret, buffer = cv2.imencode('.jpg', frame, encode_param)
                    
                    if not ret:
                        logger.error("Failed to encode frame")
                        continue
                    
                    # Convert to bytes and yield
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    
                except Exception as e:
                    logger.error(f"Error reading frame: {e}")
                    self.consecutive_failures += 1
                    time.sleep(0.1)
    
    def _generate_error_frame(self, message="No Signal"):
        """Generate a black frame with error message"""
        import numpy as np
        
        # Create black frame 640x480
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add text
        font = cv2.FONT_HERSHEY_SIMPLEX
        text_size = cv2.getTextSize(message, font, 1, 2)[0]
        text_x = (frame.shape[1] - text_size[0]) // 2
        text_y = (frame.shape[0] + text_size[1]) // 2
        
        cv2.putText(frame, message, (text_x, text_y), font, 1, (255, 255, 255), 2)
        
        # Encode as JPEG
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
        ret, buffer = cv2.imencode('.jpg', frame, encode_param)
        
        if ret:
            frame_bytes = buffer.tobytes()
            return (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        return b''
    
    def cleanup(self):
        """Release resources"""
        with self.lock:
            if self.cap is not None:
                self.cap.release()
                self.cap = None
                logger.info("Stream handler cleaned up")
