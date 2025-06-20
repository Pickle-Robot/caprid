import logging
import cv2
from datetime import datetime, timedelta
from src.config.settings import Settings
from src.stream.reolink_client import ReolinkClient
from src.stream.stream_handler import StreamHandler
from src.processing.video_processor import VideoProcessor

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def frame_callback(frame):
    """Callback function to process each frame"""
    # Display the frame (optional)
    cv2.imshow('Reolink Stream', frame)
    
    # Process the frame here
    # Example: motion detection, basic filtering, etc.
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        return False

def example_segment_recording(stream_handler):
    """Example of how to record segments with timestamps (historical only)"""
    
    # Example 1: Record a segment from 30 seconds ago to 10 seconds ago
    now = datetime.now()
    start_time = now - timedelta(seconds=30)
    end_time = now - timedelta(seconds=10)
    
    recording_id = stream_handler.start_segment_recording(
        start_time, end_time, "./output/segments/historical_segment.mp4"
    )
    
    # Example 2: Record a segment from 1 minute ago to now
    start_time2 = now - timedelta(minutes=1)
    end_time2 = now  # Current time
    
    recording_id2 = stream_handler.start_segment_recording(
        start_time2, end_time2, "./output/segments/recent_segment.mp4"
    )
    
    # Example 3: Record multiple historical segments
    timestamps = [
        (now - timedelta(seconds=60), now - timedelta(seconds=45)),  # 45-60 seconds ago
        (now - timedelta(seconds=40), now - timedelta(seconds=25)),  # 25-40 seconds ago
        (now - timedelta(seconds=20), now - timedelta(seconds=5))    # 5-20 seconds ago
    ]
    
    recording_ids = stream_handler.record_segment_from_timestamps(
        timestamps, "./output/segments"
    )
    
    print(f"Completed recordings: {[recording_id, recording_id2] + recording_ids}")

def main():
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
        return
    
    # Get video stream
    cap = client.get_video_stream(config['reolink']['channel'])
    if not cap:
        logger.error("Failed to get video stream")
        return
    
    # Initialize stream handler with 60-second buffer for historical recording
    stream_handler = StreamHandler(cap, buffer_seconds=60)
    processor = VideoProcessor()
    
    try:
        # Start streaming
        logger.info("Starting video stream...")
        stream_thread = stream_handler.start_stream(frame_callback)
        
        # Wait a moment for stream to initialize
        import time
        time.sleep(2)
        
        # Example of segment recording (uncomment to test)
        # example_segment_recording(stream_handler)
        
        # Keep the main thread alive
        stream_thread.join()
        
    except KeyboardInterrupt:
        logger.info("Stopping stream...")
    finally:
        stream_handler.stop_stream()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()