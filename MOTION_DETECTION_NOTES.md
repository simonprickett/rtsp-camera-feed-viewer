# Motion Detection Implementation Notes

## Overview
Motion detection was added on 2026-01-28 using OpenCV's MOG2 (Mixture of Gaussians) background subtraction algorithm.

## Architecture

### Server-Side (Python)
- **MotionDetector class** (`utils/stream_handler.py`) - Encapsulates all motion detection logic
- **MOG2 Algorithm** - Adaptive background subtraction that handles lighting changes and shadows
- **Frame Processing Pipeline**:
  1. Apply background subtraction to get foreground mask
  2. Remove detected shadows (set pixels with value 127 to 0)
  3. Apply binary threshold to reduce noise
  4. Morphological operations (close/open) to clean up the mask
  5. Find contours in the cleaned mask
  6. Filter contours by minimum area threshold
  7. Draw green bounding boxes around significant motion areas
  8. Add "MOTION DETECTED" text overlay when motion active

### Client-Side (JavaScript)
- **Toggle mechanism** - Click 👁️ button to enable/disable per camera
- **State management** - `cameraMotionEnabled` object tracks state per camera
- **URL parameter** - Motion state passed via `?motion=true/false` query string
- **Polling** - JavaScript polls `/api/motion/<camera_id>/<quality>` every 500ms for status
- **Visual feedback** - Motion badge pulses when motion detected
- **localStorage** - Preferences persisted across sessions

## Key Design Decisions

### 1. Reuse Stream Handlers
**Decision**: Use the same StreamHandler instance for motion on/off, just toggle the flag.

**Rationale**:
- Many IP cameras don't support multiple concurrent RTSP connections
- Creating new connections caused stream failures
- Toggling on existing handler is instant and seamless

**Implementation**:
- Stream key: `f"{camera_id}_{quality}"` (no motion state in key)
- Call `handler.set_motion_detection(enabled)` to toggle
- Same RTSP connection, different processing path

### 2. Server-Side Processing
**Decision**: Motion detection runs on server, not client.

**Rationale**:
- MJPEG streams are already decoded server-side
- Avoids sending extra data to clients
- Centralized processing, easier to optimize
- Clients just receive annotated frames

**Trade-offs**:
- Increases server CPU usage (~5-10% per camera)
- All clients see the same motion indicators
- Good for monitoring scenarios, not for per-client customization

### 3. MOG2 Over Frame Differencing
**Decision**: Use MOG2 background subtraction algorithm.

**Rationale**:
- Adaptive - learns background over time
- Handles gradual lighting changes (sunset, clouds)
- Shadow detection built-in
- More robust than simple frame differencing
- Industry standard for video surveillance

**Parameters**:
- `history=500` - Uses 500 frames to build background model (~17 seconds at 30fps)
- `varThreshold` - Configurable via sensitivity (8/16/32)
- `detectShadows=True` - Identifies and ignores shadows

### 4. Thread Safety
**Decision**: Use threading.Lock in MotionDetector.

**Rationale**:
- Multiple viewers can request the same stream
- Flask is multithreaded
- MOG2 background model is stateful
- Prevents race conditions in background model updates

### 5. Motion State Timeout
**Decision**: Keep "motion detected" flag true for 2 seconds after last motion.

**Rationale**:
- Prevents flickering indicators during brief pauses
- Smooths out intermittent detection
- Better UX for motion badge pulsing
- Configurable via `motion_timeout` parameter

## Performance Characteristics

### CPU Usage
- **Without motion**: 15-25% per camera (baseline)
- **With motion**: 20-35% per camera (+5-10%)
- **Bottleneck**: Morphological operations and contour detection
- **Optimization**: Could skip frames (process every 2nd/3rd frame)

### Memory Usage
- **MOG2 model**: ~5-10 MB per stream at 640x480
- **Additional buffers**: ~2-3 MB per stream
- **Total overhead**: ~10-15 MB per camera with motion enabled

### Latency
- **Motion detection**: Adds ~10-20ms per frame
- **Total latency**: Still 1-2 seconds (MJPEG baseline)
- **Network impact**: Minimal (same MJPEG bandwidth)

## Configuration Options

### Environment Variables
```bash
MOTION_DETECTION_ENABLED=False  # Global default (users override per-camera)
MOTION_SENSITIVITY=medium        # low=32, medium=16, high=8 (varThreshold)
MOTION_MIN_AREA=500             # Minimum contour area in pixels
```

### Sensitivity Tuning
- **Low (32)**: Good for stable scenes, minimal false positives
- **Medium (16)**: Balanced, works for most scenarios
- **High (8)**: Catches small movements, may have false positives from trees/shadows

### Minimum Area Tuning
- **500 pixels**: Default, filters small movements
- **Increase (1000+)**: Only detect large objects (people, vehicles)
- **Decrease (200-300)**: Detect smaller movements (pets, objects)

## Known Issues & Limitations

### 1. Initialization Period
- MOG2 needs ~5-10 seconds to build stable background model
- Expect false positives during this "learning" phase
- Workaround: Could add calibration indicator in UI

### 2. Lighting Changes
- Rapid lighting changes (lights turning on/off) trigger false positives
- Gradual changes (sunset) are handled well by MOG2
- Mitigation: Already using shadow detection

### 3. Static Scenes
- If camera never sees motion, background model never updates
- Could lead to stale model if camera is moved
- Mitigation: MOG2's `history` parameter keeps model fresh

### 4. Multi-Viewer Limitation
- All viewers see the same motion indicators
- Can't have per-viewer motion preferences
- Acceptable for monitoring use case

### 5. False Positives
- Trees/plants swaying in wind
- Shadows moving across scene
- Camera vibration/shake
- Mitigation: Adjust sensitivity and min area

## Future Enhancements

### Short-Term (Low Hanging Fruit)
- [ ] Frame skipping option (process every Nth frame)
- [ ] Region of Interest (ROI) selection to ignore certain areas
- [ ] Cooldown period between motion events
- [ ] Motion event logging to file/database

### Medium-Term
- [ ] Snapshot on motion (save JPEG when motion detected)
- [ ] Motion recording (save video clips with pre/post buffer)
- [ ] Webhook notifications (HTTP POST on motion events)
- [ ] Email/SMS alerts integration
- [ ] Motion heatmap overlay (show frequent motion areas)

### Long-Term
- [ ] Deep learning object detection (YOLO, SSD)
- [ ] Person detection with face recognition
- [ ] Object classification (person, vehicle, animal)
- [ ] GPU acceleration for multiple streams
- [ ] Motion zones with per-zone sensitivity

## Testing Notes

### Manual Test Checklist
- [x] Enable motion detection on camera
- [x] Verify button turns yellow
- [x] Trigger motion by waving hand
- [x] Verify green bounding boxes appear
- [x] Verify "MOTION DETECTED" text overlay
- [x] Verify motion badge pulses
- [x] Toggle quality (HD/SD) with motion enabled
- [x] Verify motion state persists across quality toggle
- [x] Reload page, verify motion preference restores
- [x] Disable motion detection
- [x] Test with multiple cameras simultaneously
- [x] Monitor CPU usage (acceptable overhead)

### Bug Fixes Applied

#### Bug #1: Stream Failure on Motion Toggle (2026-01-28)
**Problem**: Clicking 👁️ button caused stream to drop (TV static appeared).

**Root Cause**: Original implementation created separate StreamHandler instances for motion-enabled vs motion-disabled states. This created multiple concurrent RTSP connections to the same camera, which many cameras don't support.

**Solution**: Changed stream key to exclude motion state: `f"{camera_id}_{quality}"` instead of `f"{camera_id}_{quality}_motion_{enable_motion}"`. Now the same handler is reused and motion detection is toggled via `set_motion_detection(enabled)`.

**Files Changed**:
- `app.py` - video_feed() and get_motion_status() routes
- Both now use same stream key format

**Test**: Enable motion detection on all cameras simultaneously, verify all streams remain active.

## Code Quality Notes

### Error Handling
- MotionDetector.detect_motion() wrapped in try/except
- Returns original frame if motion detection fails
- Logs errors with full traceback for debugging
- Validates frame is not None before processing

### Logging
- INFO level: Handler creation, motion state changes
- DEBUG level: Per-frame motion detection results (disabled by default)
- ERROR level: Exceptions in motion processing
- All RTSP URLs sanitized (credentials removed) in logs

### Thread Safety
- MotionDetector uses threading.Lock for all state changes
- StreamHandler already had Lock for frame reading
- Safe for Flask's multithreaded mode

## API Endpoints

### GET /stream/<camera_id>/<quality>?motion=true
- Returns MJPEG stream with optional motion detection
- Query param `motion=true` enables detection
- Reuses existing handler if available
- Toggles motion detection on handler

### GET /api/motion/<camera_id>/<quality>
- Returns JSON with motion status
- Fields: `camera_id`, `quality`, `motion_enabled`, `motion_detected`
- Polls this endpoint every 500ms for real-time badge updates
- Returns 404 if camera not found
- Returns false values if no active stream

## Integration Points

### StreamHandler
- Motion detection integrated into `generate_frames()` loop
- Processes frame immediately after successful read
- Before JPEG encoding (processes raw BGR frames)
- No changes to reconnection logic

### Frontend State
- localStorage keys: `camera_${cameraId}_motion` (true/false)
- State objects: `cameraMotionEnabled`, `motionCheckIntervals`
- Button class: `.motion-toggle-btn.is-warning` when active
- Badge class: `.motion-status-badge.is-warning` when motion detected

### CSS Animations
- `motion-pulse` animation: 1s ease-in-out infinite
- Scales dot from 1.0 to 1.2 and back
- Opacity fades from 1.0 to 0.6
- Only active when `.is-warning` class present

## Maintenance Considerations

### Monitoring
- Watch for memory leaks in long-running instances
- Monitor CPU usage with multiple cameras
- Log analysis for motion detection errors
- Track false positive rates

### Upgrades
- OpenCV version updates may affect MOG2 behavior
- Test thoroughly when upgrading opencv-python
- Sensitivity tuning may need adjustment

### Debugging
- Enable DEBUG logging to see per-frame motion results
- Check browser console for JavaScript errors
- Use /api/motion endpoint to verify backend state
- Monitor Flask logs for exception tracebacks

---

**Last Updated**: 2026-01-28
**Implementation**: Simon + Claude Code
**Status**: Production Ready ✅
