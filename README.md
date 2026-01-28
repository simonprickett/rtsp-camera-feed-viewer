# RTSP Camera Viewer

A Flask-based web application for monitoring multiple RTSP camera streams in real-time with a modern Bulma CSS interface.

![RTSP Camera Viewer Screenshot](screenshot.png)

## Features

- **Flexible Camera Support** - Monitor any number of RTSP camera streams configured via JSON
- **Motion Detection** - Real-time motion detection with visual overlays and alerts
- **Quality Toggle** - Switch between main (ch0/HD) and sub (ch1/SD) streams on the fly
- **Auto-Reconnect** - Automatic reconnection when camera feeds drop
- **TV Static Animation** - Animated static display when cameras are offline
- **mDNS Support** - Works with .local hostnames (e.g., `sonoff-cam-2.local`)
- **Password Protection** - Supports RTSP authentication
- **Responsive Design** - Bulma CSS framework with mobile support
- **Local Storage** - Remembers your quality and motion detection preferences
- **Offline Operation** - All assets served locally, no internet connection required

## Prerequisites

- Python 3.7 or higher
- pip (Python package manager)
- RTSP camera streams

## Installation

1. **Clone or download this repository**

2. **Install Python dependencies**

```bash
pip install -r requirements.txt
```

The required packages are:
- Flask - Web framework
- opencv-python - RTSP stream handling and MJPEG conversion
- numpy - Image processing
- python-dotenv - Environment variable management

3. **Configure your cameras**

Edit `cameras.json` to add your camera configurations:

```json
[
  {
    "id": 1,
    "name": "Front Door",
    "url": "rtsp://thingino:thingino@sonoff-cam-1.local:554/ch0",
    "enabled": true
  },
  {
    "id": 2,
    "name": "Backyard",
    "url": "rtsp://thingino:thingino@sonoff-cam-2.local:554/ch0",
    "enabled": true
  },
  {
    "id": 3,
    "name": "Garage",
    "url": "rtsp://thingino:thingino@sonoff-cam-3.local:554/ch0",
    "enabled": true
  }
]
```

**Optional**: Copy and edit `.env` for stream settings:

```bash
cp .env.example .env
```

Edit `.env` for optional stream configuration:

```env
# Stream Settings (optional)
JPEG_QUALITY=80
RETRY_INTERVAL=5
STREAM_TIMEOUT=10
FLASK_PORT=8080
```

**RTSP URL Format:**
```
rtsp://username:password@hostname:port/path
```

For Thingino cameras:
- Main stream (high quality): `/ch0`
- Sub stream (lower quality): `/ch1`
- Default port: `554`

## Usage

1. **Start the Flask application**

```bash
python app.py
```

2. **Open your web browser**

Navigate to:
```
http://localhost:8080
```

(If you need to use a different port, change `FLASK_PORT` in your `.env` file)

3. **Toggle Stream Quality**

Click the **HD** or **SD** buttons on each camera to switch between:
- **HD (Main)** - High quality stream (ch0) - Higher bandwidth
- **SD (Sub)** - Lower quality stream (ch1) - Lower bandwidth, recommended for multiple cameras

Your quality preferences are saved automatically.

4. **Enable Motion Detection**

Click the 👁️ (eye) button on any camera to enable motion detection:
- **Green bounding boxes** appear around detected motion
- **Motion badge** pulses when movement is detected
- **"MOTION DETECTED" text** overlays the video feed
- Your motion detection preferences are saved per camera

Motion detection uses OpenCV's background subtraction algorithm and runs server-side with minimal CPU overhead.

## Motion Detection

The application supports real-time motion detection using OpenCV's MOG2 (Mixture of Gaussians) background subtraction algorithm.

### Features

- **Visual Overlays** - Green bounding boxes highlight areas with detected motion
- **Real-time Alerts** - Pulsing badge indicator when motion is active
- **Per-Camera Control** - Enable/disable independently for each camera
- **Configurable Sensitivity** - Adjust detection thresholds via environment variables
- **Persistent Preferences** - Motion settings saved to browser localStorage
- **Low Overhead** - Adds only ~5-10% CPU usage per stream

### Usage

1. Click the 👁️ button on any camera card to enable motion detection
2. The button turns yellow to indicate motion detection is active
3. Move in front of the camera to trigger detection
4. Green boxes will highlight detected motion areas
5. The motion badge will pulse when movement is detected
6. Click the 👁️ button again to disable motion detection

### Configuration

Motion detection can be fine-tuned via environment variables in `.env`:

```env
# Motion Detection Settings
MOTION_DETECTION_ENABLED=False  # Global default (users can enable per-camera)
MOTION_SENSITIVITY=medium        # Options: low, medium, high
MOTION_MIN_AREA=500             # Minimum motion area in pixels
```

**Sensitivity Levels:**
- **low** - Less sensitive, fewer false positives (e.g., trees, shadows)
- **medium** - Balanced detection (recommended)
- **high** - More sensitive, may trigger on small movements

**Min Area:** Filters out tiny movements. Increase for larger objects only, decrease for detecting small motions.

### Performance Notes

- Motion detection adds approximately **5-10% CPU overhead** per camera
- The background subtraction algorithm is highly optimized
- Enable motion detection on 2-3 cameras simultaneously on typical hardware
- Disable motion detection when not needed to conserve resources
- The MOG2 algorithm adapts to lighting changes automatically

### How It Works (Technical Details)

Motion detection is implemented using OpenCV's **MOG2 (Mixture of Gaussians)** background subtraction algorithm. Here's the processing pipeline:

#### 1. Background Model
- MOG2 maintains a **statistical model** of the background scene
- Uses the **last 500 frames** (~17 seconds at 30fps) to build the model
- Adapts automatically to gradual lighting changes (clouds, sunset)
- Each pixel is modeled as a mixture of Gaussian distributions

#### 2. Frame Processing Pipeline
When motion detection is enabled, each video frame goes through these steps:

1. **Background Subtraction** - Compare current frame to background model
2. **Shadow Removal** - Detect and remove shadows (reduces false positives)
3. **Binary Threshold** - Create clean foreground/background mask
4. **Noise Reduction** - Morphological operations (closing/opening) to clean up small artifacts
5. **Contour Detection** - Find connected regions of motion
6. **Area Filtering** - Ignore contours smaller than minimum area (default: 500 pixels)
7. **Bounding Boxes** - Draw green rectangles around significant motion regions
8. **Overlay Text** - Add "MOTION DETECTED" indicator when motion is present

#### 3. Server-Side Processing
- Motion detection runs on the **Flask server**, not in the browser
- Processes frames in the existing RTSP → MJPEG conversion pipeline
- All connected clients see the same motion indicators
- No additional bandwidth required (same MJPEG stream)

#### 4. Real-Time Updates
- JavaScript polls `/api/motion/<camera_id>/<quality>` every **500ms**
- Updates motion badge indicator based on detection status
- Badge pulses (yellow) when motion is actively detected
- Preferences saved to browser **localStorage** for persistence

#### 5. Initialization Period
- MOG2 needs **5-10 seconds** after enabling to build a stable background model
- During this "learning phase", expect some false positives
- Once stabilized, detection becomes very accurate
- Model continuously updates to adapt to scene changes

#### 6. Thread Safety
- Uses threading locks to handle multiple concurrent viewers
- Safe for Flask's multithreaded environment
- Each camera/quality combination has one shared StreamHandler instance

#### Key Algorithm Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `history` | 500 frames | How many frames to use for background model |
| `varThreshold` | 16 (medium) | Pixel variance threshold (lower = more sensitive) |
| `detectShadows` | True | Identify and ignore moving shadows |
| `min_contour_area` | 500 pixels | Minimum size to consider as motion |
| `motion_timeout` | 2.0 seconds | How long to keep "motion detected" flag active |

#### Why MOG2?

We chose MOG2 over simpler approaches (frame differencing) because:
- **Adaptive** - Learns and updates background automatically
- **Robust** - Handles lighting changes, shadows, and camera noise
- **Efficient** - Highly optimized C++ implementation in OpenCV
- **Industry Standard** - Proven in commercial surveillance systems
- **Low Latency** - Processes 640x480 frames in ~10-20ms

#### Developer Notes

For detailed implementation notes, architecture decisions, and future enhancement ideas, see [MOTION_DETECTION_NOTES.md](MOTION_DETECTION_NOTES.md).

## Configuration Options

### Camera Configuration (cameras.json)

Each camera entry supports:

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique numeric camera identifier |
| `name` | Yes | Display name for the camera |
| `url` | Yes | RTSP camera URL (format: `rtsp://username:password@hostname:port/path`) |
| `enabled` | No | Enable/disable camera (default: true) |

Add or remove cameras as needed - the application dynamically loads all enabled cameras.

### Environment Variables (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_PORT` | 5000 | Web server port |
| `FLASK_DEBUG` | False | Enable debug mode |
| `FLASK_SECRET_KEY` | - | Flask secret key for sessions |
| `JPEG_QUALITY` | 80 | JPEG compression quality (1-100) |
| `RETRY_INTERVAL` | 5 | Seconds between reconnection attempts |
| `STREAM_TIMEOUT` | 10 | Connection timeout in seconds |
| `MOTION_DETECTION_ENABLED` | False | Global default for motion detection |
| `MOTION_SENSITIVITY` | medium | Motion sensitivity: low, medium, or high |
| `MOTION_MIN_AREA` | 500 | Minimum motion area in pixels |

### JPEG Quality

- **90-100**: Highest quality, largest bandwidth
- **75-85**: Good balance (recommended)
- **60-70**: Lower quality, reduced bandwidth
- **Below 60**: Noticeable quality loss

## Troubleshooting

### Camera not connecting

1. **Check RTSP URL** - Verify hostname, port, path, and credentials
2. **Test with VLC** - Try opening the RTSP URL in VLC Media Player
3. **Network connectivity** - Ensure cameras are reachable from your computer
4. **Firewall** - Check firewall rules for port 554 (RTSP)

### .local domains not resolving

- **macOS**: Should work out of the box (Bonjour/mDNS built-in)
- **Alternative**: Use IP addresses instead: `rtsp://username:password@192.168.1.100:554/ch0`

### High CPU usage

1. **Use sub streams** - Toggle to SD quality (ch1) for lower resolution
2. **Reduce JPEG quality** - Lower `JPEG_QUALITY` in `.env`
3. **Fewer simultaneous viewers** - Each browser connection creates a new stream

### Streams keep disconnecting

1. **Check network stability** - WiFi signal strength, bandwidth
2. **Camera health** - Some cameras struggle with multiple connections
3. **Increase timeout** - Set higher `STREAM_TIMEOUT` in `.env`

### TV static not appearing

1. **Check browser console** - Press F12 and look for JavaScript errors
2. **Canvas support** - Ensure browser supports HTML5 Canvas
3. **Try different browser** - Test in Chrome, Firefox, or Safari

### Motion detection not working

1. **Check button state** - Ensure 👁️ button is yellow (active)
2. **Trigger motion** - Move in front of camera to test detection
3. **Adjust sensitivity** - Try `MOTION_SENSITIVITY=high` in `.env`
4. **Check CPU usage** - Motion detection requires processing power
5. **Browser console** - Press F12 and check for API errors

### Too many false motion alerts

1. **Reduce sensitivity** - Set `MOTION_SENSITIVITY=low` in `.env`
2. **Increase min area** - Set `MOTION_MIN_AREA=1000` or higher
3. **Check camera placement** - Avoid areas with trees, flags, or busy backgrounds
4. **Lighting conditions** - MOG2 adapts but extreme changes may trigger false positives

## Project Structure

```
rtsp-cam-viewer/
├── app.py                       # Flask application and routes
├── config.py                    # Configuration management
├── cameras.json                 # Camera configurations
├── requirements.txt             # Python dependencies
├── README.md                    # User documentation (this file)
├── MOTION_DETECTION_NOTES.md    # Technical implementation notes
├── .env                         # Environment variables (optional)
├── .env.example                 # Example configuration
├── .gitignore                   # Git ignore rules
│
├── static/
│   ├── css/
│   │   ├── bulma.min.css        # Bulma CSS framework (local)
│   │   └── style.css            # Custom styles
│   └── js/
│       └── app.js               # Client-side logic, TV static, motion detection
│
├── templates/
│   └── index.html               # Main HTML template
│
└── utils/
    ├── __init__.py
    └── stream_handler.py        # RTSP stream processing & motion detection
```

## Technology Stack

- **Backend**: Flask (Python web framework)
- **Video Processing**: OpenCV (RTSP capture, MJPEG encoding, MOG2 motion detection)
- **Frontend**: Bulma CSS (local), Vanilla JavaScript
- **Streaming**: MJPEG over HTTP (multipart/x-mixed-replace)
- **Motion Detection**: MOG2 background subtraction algorithm
- **Icons**: Unicode symbols (no external dependencies)

## Security Notes

- **Protect `cameras.json`** - Contains camera credentials and URLs
- **Never commit credentials** - Consider using environment variables for passwords
- **Use strong passwords** - Change default camera passwords
- **Network isolation** - Consider VLANs or separate networks for cameras
- **HTTPS in production** - Use reverse proxy (nginx, Apache) with SSL

## Known Limitations

- **Latency**: MJPEG has ~1-2 second delay (acceptable for monitoring)
- **Bandwidth**: Each viewer creates a separate stream
- **No audio**: Current implementation is video-only
- **Browser limit**: Most browsers limit ~6 simultaneous connections per domain
- **Motion detection initialization**: MOG2 needs 5-10 seconds to build background model after enabling
- **Motion detection false positives**: Trees, shadows, and lighting changes may trigger false alerts (adjustable via sensitivity)

## Future Enhancements

- [x] Motion detection with visual overlays (✓ Implemented)
- [ ] Recording/snapshot capability
- [ ] PTZ (Pan-Tilt-Zoom) controls
- [ ] Motion detection recording (save clips when motion detected)
- [ ] Motion detection notifications (email/SMS alerts)
- [ ] User authentication
- [ ] HLS streaming option for lower latency
- [ ] Multi-user support with stream sharing

## License

This project is open source and available for personal and commercial use.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review [MOTION_DETECTION_NOTES.md](MOTION_DETECTION_NOTES.md) for technical details
3. Review Flask and OpenCV documentation
4. Test RTSP streams with VLC Media Player first

## Credits

Built with:
- [Flask](https://flask.palletsprojects.com/)
- [OpenCV](https://opencv.org/)
- [Bulma CSS](https://bulma.io/)
- [Font Awesome](https://fontawesome.com/)
