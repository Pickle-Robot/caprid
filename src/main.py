import logging
import time
import signal
import sys
from datetime import datetime, timedelta
from src.config.settings import Settings
from src.stream.reolink_client import ReolinkClient
from src.stream.stream_handler import StreamHandler
from src.processing.video_processor import VideoProcessor

# Global flag for graceful shutdown
running = True

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global running
    print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
    running = False

def frame_callback(frame):
    """Callback function to process each frame"""
    # Process frames here without displaying
    # Example: motion detection, frame analysis, etc.
    
    # For headless operation, we don't display frames
    # but we can still process them
    global running
    
    if not running:
        return False
    
    # Optional: Print frame info periodically
    if hasattr(frame_callback, 'frame_count'):
        frame_callback.frame_count += 1
    else:
        frame_callback.frame_count = 1
    
    # Print status every 300 frames (about 10 seconds at 30fps)
    if frame_callback.frame_count % 300 == 0:
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"📹 [{timestamp}] Processed {frame_callback.frame_count} frames, Frame size: {frame.shape}")
    
    return True

def example_segment_recording(stream_handler):
    """Example of how to record segments with timestamps (historical only)"""
    print("📹 Recording example segments...")
    
    # Example 1: Record a segment from 30 seconds ago to 10 seconds ago
    now = datetime.now()
    start_time = now - timedelta(seconds=30)
    end_time = now - timedelta(seconds=10)
    
    recording_id = stream_handler.start_segment_recording(
        start_time, end_time, "./output/segments/historical_segment.mp4"
    )
    
    if recording_id:
        print(f"✅ Recorded segment: {recording_id}")
    
    # Example 2: Record multiple historical segments
    timestamps = [
        (now - timedelta(seconds=60), now - timedelta(seconds=45)),  # 45-60 seconds ago
        (now - timedelta(seconds=40), now - timedelta(seconds=25)),  # 25-40 seconds ago
        (now - timedelta(seconds=20), now - timedelta(seconds=5))    # 5-20 seconds ago
    ]
    
    recording_ids = stream_handler.record_segment_from_timestamps(
        timestamps, "./output/segments"
    )
    
    print(f"✅ Completed {len(recording_ids)} additional recordings")

def main():
    global running
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Load configuration
    settings = Settings()
    config = settings.config
    
    # Initialize Reolink client
    client = ReolinkClient(
        host=config['reolink']['host'],
        username=config['reolink']['username'],
        password=config['reolink']['password'],
        port=config['reolink']['port']
    )
    
    # Authenticate
    if not client.authenticate():
        logger.error("Failed to authenticate with camera")
        return 1
    
    # Get video stream
    cap = client.get_video_stream(config['reolink']['channel'])
    if not cap:
        logger.error("Failed to get video stream")
        return 1
    
    # Initialize stream handler with buffer for historical recording
    stream_handler = StreamHandler(cap, buffer_seconds=60)
    processor = VideoProcessor()
    
    try:
        # Start streaming
        logger.info("🎥 Starting video stream processing...")
        logger.info("📊 Running in headless mode (no display)")
        logger.info("🔄 Processing frames in background...")
        
        stream_thread = stream_handler.start_stream(frame_callback)
        
        # Wait for stream to initialize
        time.sleep(3)
        
        # Example of segment recording (uncomment to test)
        # logger.info("📹 Testing segment recording...")
        # example_segment_recording(stream_handler)
        
        logger.info("✅ Stream processing started successfully")
        logger.info("ℹ️ Press Ctrl+C to stop")
        
        # Keep the main thread alive and monitor
        frame_count = 0
        while running and stream_thread.is_alive():
            time.sleep(5)  # Check every 5 seconds
            
            # Get current frame info
            current_frame = stream_handler.get_current_frame()
            if current_frame is not None:
                frame_count += 1
                if frame_count % 12 == 0:  # Every minute
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    logger.info(f"📊 [{timestamp}] Stream active, latest frame: {current_frame.shape}")
        
        if not running:
            logger.info("🛑 Shutdown requested by user")
        else:
            logger.warning("⚠️ Stream thread stopped unexpectedly")
        
    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user")
        running = False
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        return 1
    finally:
        logger.info("🔄 Cleaning up...")
        stream_handler.stop_stream()
        if cap:
            cap.release()
        logger.info("✅ Cleanup complete")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)