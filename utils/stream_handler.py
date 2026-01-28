"""
Stream handler for RTSP to MJPEG conversion
"""
import cv2
import time
import logging
from threading import Lock

logger = logging.getLogger(__name__)


class MotionDetector:
    """Handle motion detection using background subtraction"""

    def __init__(self, sensitivity='medium', min_contour_area=500):
        self.enabled = False
        self.motion_detected = False
        self.last_motion_time = 0
        self.motion_timeout = 2.0  # seconds to keep "motion detected" state

        # Sensitivity mapping to MOG2 varThreshold
        sensitivity_map = {
            'low': 32,      # Less sensitive, fewer false positives
            'medium': 16,   # Balanced
            'high': 8       # More sensitive, may have more false positives
        }
        var_threshold = sensitivity_map.get(sensitivity, 16)

        # Initialize background subtractor
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500,
            varThreshold=var_threshold,
            detectShadows=True
        )

        self.min_contour_area = min_contour_area
        self.lock = Lock()

    def detect_motion(self, frame):
        """
        Detect motion in frame and return annotated frame with bounding boxes

        Returns:
            tuple: (annotated_frame, motion_detected)
        """
        if not self.enabled:
            return frame, False

        # Check if frame is valid
        if frame is None or frame.size == 0:
            logger.warning("Invalid frame received for motion detection")
            return frame, False

        try:
            with self.lock:
                # Apply background subtraction
                fg_mask = self.bg_subtractor.apply(frame)

                # Remove shadows (set to 0)
                fg_mask[fg_mask == 127] = 0

                # Apply threshold to reduce noise
                _, fg_mask = cv2.threshold(fg_mask, 244, 255, cv2.THRESH_BINARY)

                # Morphological operations to reduce noise
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
                fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)

                # Find contours
                contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                # Filter contours by area and draw bounding boxes
                motion_detected = False
                annotated_frame = frame.copy()

                for contour in contours:
                    area = cv2.contourArea(contour)
                    if area > self.min_contour_area:
                        motion_detected = True
                        # Draw bounding box
                        x, y, w, h = cv2.boundingRect(contour)
                        cv2.rectangle(annotated_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # Update motion state
                if motion_detected:
                    self.motion_detected = True
                    self.last_motion_time = time.time()
                else:
                    # Keep motion_detected True for timeout period
                    if time.time() - self.last_motion_time > self.motion_timeout:
                        self.motion_detected = False

                # Add motion indicator overlay
                if self.motion_detected:
                    cv2.putText(annotated_frame, "MOTION DETECTED", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                return annotated_frame, self.motion_detected

        except Exception as e:
            logger.error(f"Error in motion detection: {e}", exc_info=True)
            # Return original frame if motion detection fails
            return frame, False

    def set_enabled(self, enabled):
        """Enable or disable motion detection"""
        with self.lock:
            self.enabled = enabled
            if enabled:
                # Reset background model when enabling
                self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                    history=500,
                    varThreshold=16,
                    detectShadows=True
                )

    def is_motion_detected(self):
        """Check if motion is currently detected"""
        return self.motion_detected


class StreamHandler:
    """Handle RTSP stream capture and MJPEG conversion"""
    
    def __init__(self, rtsp_url, jpeg_quality=80, timeout=10, retry_interval=5,
                 enable_motion_detection=False, motion_sensitivity='medium', motion_min_area=500):
        self.rtsp_url = rtsp_url
        self.jpeg_quality = jpeg_quality
        self.timeout = timeout
        self.retry_interval = retry_interval
        self.cap = None
        self.lock = Lock()
        self.consecutive_failures = 0
        self.max_failures = 3

        # Initialize motion detector
        self.motion_detector = MotionDetector(
            sensitivity=motion_sensitivity,
            min_contour_area=motion_min_area
        )
        self.motion_detector.set_enabled(enable_motion_detection)
        
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

                    # Apply motion detection if enabled
                    if self.motion_detector.enabled:
                        logger.debug("Applying motion detection to frame")
                        frame, motion_detected = self.motion_detector.detect_motion(frame)
                        logger.debug(f"Motion detection result: {motion_detected}")

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
    
    def set_motion_detection(self, enabled):
        """Enable or disable motion detection"""
        self.motion_detector.set_enabled(enabled)
        logger.info(f"Motion detection {'enabled' if enabled else 'disabled'} for {self._sanitize_url(self.rtsp_url)}")

    def is_motion_detected(self):
        """Check if motion is currently detected"""
        return self.motion_detector.is_motion_detected()

    def cleanup(self):
        """Release resources"""
        with self.lock:
            if self.cap is not None:
                self.cap.release()
                self.cap = None
                logger.info("Stream handler cleaned up")
