#!/bin/bash
# Run script with example segment recording enabled

echo "🎥📹 Starting Reolink Stream Processor with Recording Examples..."

# Activate virtual environment
source venv/bin/activate

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | grep -v '#' | xargs)
fi

# Temporary modify main.py to enable example recording
echo "🔧 Enabling example recording..."

# Create a temporary main file with recording enabled
python3 << 'EOF'
import sys
sys.path.append('src')

from datetime import datetime, timedelta
import logging
import cv2
from config.settings import Settings
from stream.reolink_client import ReolinkClient
from stream.stream_handler import StreamHandler
from processing.video_processor import VideoProcessor

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def frame_callback(frame):
    cv2.imshow('Reolink Stream', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        return False

def example_recording(stream_handler):
    print("📹 Recording example segments...")
    now = datetime.now()
    
    # Record last 30 seconds
    start_time = now - timedelta(seconds=30)
    end_time = now
    
    recording_id = stream_handler.start_segment_recording(
        start_time, end_time, "./output/segments/last_30_seconds.mp4"
    )
    print(f"✅ Recorded last 30 seconds: {recording_id}")
    
    # Record multiple segments
    timestamps = [
        (now - timedelta(seconds=60), now - timedelta(seconds=45)),
        (now - timedelta(seconds=40), now - timedelta(seconds=25)),
        (now - timedelta(seconds=20), now - timedelta(seconds=5))
    ]
    
    recording_ids = stream_handler.record_segment_from_timestamps(
        timestamps, "./output/segments"
    )
    print(f"✅ Recorded {len(recording_ids)} additional segments")

def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    
    settings = Settings()
    config = settings.config
    
    client = ReolinkClient(
        host=config['reolink']['host'],
        username=config['reolink']['username'],
        password=config['reolink']['password'],
        port=config['reolink']['port']
    )
    
    if not client.authenticate():
        logger.error("Failed to authenticate with camera")
        return
    
    cap = client.get_video_stream(config['reolink']['channel'])
    if not cap:
        logger.error("Failed to get video stream")
        return
    
    stream_handler = StreamHandler(cap, buffer_seconds=120)
    
    try:
        logger.info("Starting video stream...")
        stream_thread = stream_handler.start_stream(frame_callback)
        
        # Wait for buffer to populate
        import time
        time.sleep(10)
        
        # Run example recording
        example_recording(stream_handler)
        
        # Keep running
        stream_thread.join()
        
    except KeyboardInterrupt:
        logger.info("Stopping stream...")
    finally:
        stream_handler.stop_stream()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
EOF

echo "👋 Recording demo complete! Check ./output/segments/ for files"
