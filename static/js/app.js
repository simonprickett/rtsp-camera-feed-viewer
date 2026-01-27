/**
 * RTSP Camera Viewer - Client-side JavaScript
 * Handles TV static animation, stream error detection, and quality toggle
 */

// Configuration
const RETRY_INTERVAL = 5000; // 5 seconds
const STATIC_FPS = 30; // Frames per second for TV static

// Store retry timeouts
const retryTimeouts = {};

// Store stream health check timeouts
const healthCheckTimeouts = {};

// Store last frame update time for each camera
const lastFrameUpdate = {
    1: Date.now(),
    2: Date.now(),
    3: Date.now()
};
const cameraQuality = {
    1: 'main',
    2: 'main',
    3: 'main'
};

/**
 * Check if stream is actually receiving frames
 */
function checkStreamHealth(cameraId) {
    const streamImg = document.getElementById(`stream-${cameraId}`);
    if (!streamImg) return;
    
    // Check if image has valid dimensions (actually loaded)
    const hasValidImage = streamImg.naturalWidth > 0 && streamImg.naturalHeight > 0;
    
    if (!hasValidImage) {
        console.log(`Camera ${cameraId} has no valid image - triggering error handler`);
        handleStreamError(cameraId);
        return;
    }
    
    // Schedule next health check
    healthCheckTimeouts[cameraId] = setTimeout(() => {
        checkStreamHealth(cameraId);
    }, 3000); // Check every 3 seconds
}

/**
 * Initialize TV static canvas for a camera
 */
function initStaticCanvas(cameraId) {
    const canvas = document.getElementById(`static-${cameraId}`);
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    let animationId = null;
    
    function renderStatic() {
        const imageData = ctx.createImageData(canvas.width, canvas.height);
        const data = imageData.data;
        
        // Generate random noise
        for (let i = 0; i < data.length; i += 4) {
            const color = Math.random() * 255;
            data[i] = color;     // R
            data[i + 1] = color; // G
            data[i + 2] = color; // B
            data[i + 3] = 255;   // A
        }
        
        ctx.putImageData(imageData, 0, 0);
        
        // Continue animation if canvas is visible
        if (canvas.style.display !== 'none') {
            animationId = setTimeout(() => {
                requestAnimationFrame(renderStatic);
            }, 1000 / STATIC_FPS);
        }
    }
    
    // Store animation control
    canvas.startStatic = () => {
        canvas.style.display = 'block';
        if (!animationId) {
            renderStatic();
        }
    };
    
    canvas.stopStatic = () => {
        if (animationId) {
            clearTimeout(animationId);
            animationId = null;
        }
        canvas.style.display = 'none';
    };
}

/**
 * Handle stream error - show TV static and attempt reconnection
 */
function handleStreamError(cameraId) {
    console.log(`Stream error for camera ${cameraId} - showing TV static`);
    
    const streamImg = document.getElementById(`stream-${cameraId}`);
    const staticCanvas = document.getElementById(`static-${cameraId}`);
    const statusTag = document.getElementById(`status-${cameraId}`);
    const reconnectingOverlay = document.getElementById(`reconnecting-${cameraId}`);
    
    if (!streamImg || !staticCanvas) {
        console.error(`Missing elements for camera ${cameraId}`);
        return;
    }
    
    // Hide stream, show static
    streamImg.style.display = 'none';
    console.log(`Starting TV static for camera ${cameraId}`);
    
    // Start static animation
    if (staticCanvas.startStatic) {
        staticCanvas.startStatic();
    } else {
        console.warn(`Static animation not initialized for camera ${cameraId}`);
    }
    
    // Update status
    if (statusTag) {
        statusTag.className = 'tag is-danger is-light';
        statusTag.innerHTML = '<span>●</span><span>Offline</span>';
    }
    
    // Clear existing retry timeout
    if (retryTimeouts[cameraId]) {
        clearTimeout(retryTimeouts[cameraId]);
    }
    
    // Schedule reconnection attempt
    retryTimeouts[cameraId] = setTimeout(() => {
        attemptReconnect(cameraId);
    }, RETRY_INTERVAL);
}

/**
 * Attempt to reconnect stream
 */
function attemptReconnect(cameraId) {
    console.log(`Attempting to reconnect camera ${cameraId}`);
    
    const streamImg = document.getElementById(`stream-${cameraId}`);
    const quality = cameraQuality[cameraId];
    
    if (!streamImg) return;
    
    // Add timestamp to bypass cache
    const timestamp = new Date().getTime();
    const newSrc = `/stream/${cameraId}/${quality}?t=${timestamp}`;
    
    // Set up handlers for this reconnection attempt
    streamImg.onload = () => {
        // Verify the image actually loaded with valid dimensions
        if (streamImg.naturalWidth > 0 && streamImg.naturalHeight > 0) {
            console.log(`Reconnection successful for camera ${cameraId}`);
            handleStreamSuccess(cameraId);
        } else {
            console.log(`Reconnection failed for camera ${cameraId} - no valid image`);
            handleStreamError(cameraId);
        }
    };
    
    streamImg.onerror = () => {
        console.log(`Reconnection failed for camera ${cameraId} - error event`);
        handleStreamError(cameraId);
    };
    
    // Reload stream
    streamImg.src = newSrc;
    
    // Set a timeout to check if reconnection is taking too long
    setTimeout(() => {
        if (streamImg.naturalWidth === 0 || streamImg.naturalHeight === 0) {
            console.log(`Reconnection timeout for camera ${cameraId}`);
            handleStreamError(cameraId);
        }
    }, 3000);
}

/**
 * Handle successful stream connection
 */
function handleStreamSuccess(cameraId) {
    console.log(`Stream connected for camera ${cameraId}`);
    
    const streamImg = document.getElementById(`stream-${cameraId}`);
    const staticCanvas = document.getElementById(`static-${cameraId}`);
    const statusTag = document.getElementById(`status-${cameraId}`);
    const reconnectingOverlay = document.getElementById(`reconnecting-${cameraId}`);
    
    // Show stream, hide static
    if (streamImg) {
        streamImg.style.display = 'block';
    }
    if (staticCanvas && staticCanvas.stopStatic) {
        staticCanvas.stopStatic();
    }
    
    // Update status
    if (statusTag) {
        statusTag.className = 'tag is-success is-light';
        statusTag.innerHTML = '<span>●</span><span>Live</span>';
    }
    
    // Restart health checks
    if (healthCheckTimeouts[cameraId]) {
        clearTimeout(healthCheckTimeouts[cameraId]);
    }
    setTimeout(() => {
        checkStreamHealth(cameraId);
    }, 3000);
}

/**
 * Toggle stream quality (main/sub)
 */
function toggleQuality(cameraId, quality) {
    console.log(`Switching camera ${cameraId} to ${quality} quality`);
    
    const streamImg = document.getElementById(`stream-${cameraId}`);
    const qualityTag = document.getElementById(`quality-tag-${cameraId}`);
    const buttons = document.querySelectorAll(`[data-camera="${cameraId}"]`);
    
    if (!streamImg) return;
    
    // Update stored quality
    cameraQuality[cameraId] = quality;
    
    // Update button states
    buttons.forEach(btn => {
        if (btn.dataset.quality === quality) {
            btn.classList.add('active', 'is-link');
        } else {
            btn.classList.remove('active', 'is-link');
        }
    });
    
    // Update quality tag
    if (qualityTag) {
        if (quality === 'main') {
            qualityTag.textContent = 'Main Stream (ch0)';
        } else {
            qualityTag.textContent = 'Sub Stream (ch1)';
        }
    }
    
    // Save preference to localStorage
    localStorage.setItem(`camera_${cameraId}_quality`, quality);
    
    // Update stream source
    const timestamp = new Date().getTime();
    streamImg.src = `/stream/${cameraId}/${quality}?t=${timestamp}`;
}

/**
 * Load saved quality preferences
 */
function loadQualityPreferences() {
    for (let cameraId = 1; cameraId <= 3; cameraId++) {
        const savedQuality = localStorage.getItem(`camera_${cameraId}_quality`);
        if (savedQuality && (savedQuality === 'main' || savedQuality === 'sub')) {
            // Apply saved preference
            toggleQuality(cameraId, savedQuality);
        }
    }
}

/**
 * Initialize application
 */
function init() {
    console.log('Initializing RTSP Camera Viewer');
    
    // Initialize TV static for all cameras
    for (let cameraId = 1; cameraId <= 3; cameraId++) {
        initStaticCanvas(cameraId);
        
        // Set up error handler for stream images
        const streamImg = document.getElementById(`stream-${cameraId}`);
        if (streamImg) {
            streamImg.onerror = () => handleStreamError(cameraId);
            
            // Start health check after a brief delay to allow initial load
            setTimeout(() => {
                checkStreamHealth(cameraId);
            }, 2000);
        }
    }
    
    // Add click handlers to quality buttons
    const qualityButtons = document.querySelectorAll('.quality-btn');
    qualityButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const cameraId = parseInt(this.dataset.camera);
            const quality = this.dataset.quality;
            toggleQuality(cameraId, quality);
        });
    });
    
    // Load saved preferences
    loadQualityPreferences();
    
    console.log('Initialization complete');
}
    // Clear all health check timeouts
    Object.values(healthCheckTimeouts).forEach(timeout => clearTimeout(timeout));

// Run initialization when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    // Clear all retry timeouts
    Object.values(retryTimeouts).forEach(timeout => clearTimeout(timeout));
});
