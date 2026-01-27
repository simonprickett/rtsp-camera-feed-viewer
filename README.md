# RTSP Camera Viewer

A Flask-based web application for monitoring multiple RTSP camera streams in real-time with a modern Bulma CSS interface.

![RTSP Camera Viewer Screenshot](screenshot.png)

## Features

- **3 Camera Support** - Monitor up to 3 RTSP camera streams simultaneously
- **Quality Toggle** - Switch between main (ch0/HD) and sub (ch1/SD) streams on the fly
- **Auto-Reconnect** - Automatic reconnection when camera feeds drop
- **TV Static Animation** - Animated static display when cameras are offline
- **mDNS Support** - Works with .local hostnames (e.g., `sonoff-cam-2.local`)
- **Password Protection** - Supports RTSP authentication
- **Responsive Design** - Bulma CSS framework with mobile support
- **Local Storage** - Remembers your quality preferences
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

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your camera URLs:

```env
# Camera Configuration
CAM_1=rtsp://thingino:thingino@sonoff-cam-1.local:554/ch0
CAM_2=rtsp://thingino:thingino@sonoff-cam-2.local:554/ch0
CAM_3=rtsp://thingino:thingino@sonoff-cam-3.local:554/ch0

# Optional: Camera display names
CAM_1_NAME=Front Door
CAM_2_NAME=Backyard
CAM_3_NAME=Garage

# Stream Settings (optional)
JPEG_QUALITY=80
RETRY_INTERVAL=5
STREAM_TIMEOUT=10
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

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CAM_1`, `CAM_2808`CAM_3` | - | RTSP camera URLs |
| `CAM_1_NAME`, `CAM_2_NAME`, `CAM_3_NAME` | Camera 1/2/3 | Display names |
| `FLASK_PORT` | 5000 | Web server port |
| `FLASK_DEBUG` | False | Enable debug mode |
| `JPEG_QUALITY` | 80 | JPEG compression quality (1-100) |
| `RETRY_INTERVAL` | 5 | Seconds between reconnection attempts |
| `STREAM_TIMEOUT` | 10 | Connection timeout in seconds |

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

## Project Structure

```
rtsp-cam-viewer/
├── app.py                  # Flask application and routes
├── config.py               # Configuration management
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (create from .env.example)
├── .env.example           # Example configuration
├── .gitignore             # Git ignore rules
│
├── static/
│   ├── css/
│   │   └── style.css      # Custom styles
│   └── js/
│       └── app.js         # Client-side logic and TV static
│
├── templates/
│   └── index.html         # Main HTML template
│
└── utils/
    ├── __init__.py
    └── stream_handler.py  # RTSP stream processing
```

## Technology Stack

- **Backend**: Flask (Python web framework)
- **Video Processing**: OpenCV (RTSP capture and MJPEG encoding)
- **Frontend**: Bulma CSS (local), Vanilla JavaScript
- **Streaming**: MJPEG over HTTP (multipart/x-mixed-replace)
- **Icons**: Unicode symbols (no external dependencies)

## Security Notes

- **Never commit `.env`** - Contains camera credentials
- **Use strong passwords** - Change default camera passwords
- **Network isolation** - Consider VLANs or separate networks for cameras
- **HTTPS in production** - Use reverse proxy (nginx, Apache) with SSL

## Known Limitations

- **Latency**: MJPEG has ~1-2 second delay (acceptable for monitoring)
- **Bandwidth**: Each viewer creates a separate stream
- **No audio**: Current implementation is video-only
- **Browser limit**: Most browsers limit ~6 simultaneous connections per domain

## Future Enhancements

- [ ] Recording/snapshot capability
- [ ] PTZ (Pan-Tilt-Zoom) controls
- [ ] Motion detection alerts
- [ ] User authentication
- [ ] HLS streaming option for lower latency
- [ ] Multi-user support with stream sharing

## License

This project is open source and available for personal and commercial use.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Flask and OpenCV documentation
3. Test RTSP streams with VLC Media Player first

## Credits

Built with:
- [Flask](https://flask.palletsprojects.com/)
- [OpenCV](https://opencv.org/)
- [Bulma CSS](https://bulma.io/)
- [Font Awesome](https://fontawesome.com/)
