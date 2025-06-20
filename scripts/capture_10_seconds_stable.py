"""
Capture exactly 10 seconds of video from the Reolink camera with error suppression
"""

import logging
import time
import os
from datetime import datetime, timedelta
from src.config.settings import Settings
from src.stream.reolink_client import ReolinkClient
from src.stream.stream_handler import StreamHandler

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def suppress_ffmpeg_logs():
    """Suppress FFmpeg/OpenCV video codec error messages"""
    os.environ['OPENCV_FFMPEG_LOGLEVEL'] = '-8'  # Suppress all FFmpeg logs
    os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'     # Only show OpenCV errors

def main():
    # Suppress codec error messages
    suppress_ffmpeg_logs()
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    print("📹 Starting 10-second video capture (stable mode)...")
    
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
        logger.error("❌ Failed to authenticate with camera")
        return 1
    
    # Get video stream - try sub-stream first for stability
    logger.info("🎥 Attempting sub-stream for better stability...")
    
    # Try sub-stream URL first (usually more stable)
    import cv2
    sub_stream_url = f"rtsp://{config['reolink']['username']}:{config['reolink']['password']}@{config['reolink']['host']}:554/h264Preview_01_sub"
    
    cap = cv2.VideoCapture(sub_stream_url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FPS, 10)  # Lower FPS for stability
    
    if not cap.isOpened():
        logger.info("Sub-stream failed, trying main stream...")
        cap = client.get_video_stream(config['reolink']['channel'])
        if not cap:
            logger.error("❌ Failed to get video stream")
            return 1
    else:
        logger.info("✅ Using sub-stream for capture")
    
    # Initialize stream handler with buffer
    stream_handler = StreamHandler(cap, buffer_seconds=30)
    
    try:
        # Start streaming
        logger.info("🎥 Starting video stream...")
        stream_thread = stream_handler.start_stream()
        
        # Wait for stream to initialize
        time.sleep(3)  # Longer wait for stability
        logger.info("✅ Stream initialized")
        
        # Capture 10 seconds starting from now
        now = datetime.now()
        start_time = now
        end_time = now + timedelta(seconds=10)
        
        # Generate filename with timestamp
        filename = f"capture_{now.strftime('%Y%m%d_%H%M%S')}_10sec_stable.mp4"
        output_path = f"./output/segments/{filename}"
        
        logger.info(f"📹 Recording 10 seconds to: {filename}")
        logger.info(f"⏱️  Start: {start_time.strftime('%H:%M:%S')}")
        logger.info(f"⏱️  End:   {end_time.strftime('%H:%M:%S')}")
        
        # Wait for the full 10 seconds to pass
        print("🔴 Recording in progress...")
        for i in range(10):
            time.sleep(1)
            remaining = 10 - i - 1
            if remaining > 0:
                print(f"⏱️  {remaining} seconds remaining...", end='\r')
            else:
                print("⏱️  Recording complete!     ")
        
        # Now capture the 10 seconds that just passed
        actual_end_time = datetime.now()
        recording_id = stream_handler.start_segment_recording(
            start_time, 
            actual_end_time, 
            output_path
        )
        
        if recording_id:
            logger.info(f"✅ Video captured successfully!")
            logger.info(f"📁 File saved: {output_path}")
            
            # Check file size
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
                logger.info(f"📊 File size: {file_size:.1f} MB")
            else:
                logger.warning("⚠️ File not found after recording")
        else:
            logger.error("❌ Failed to capture video")
            return 1
        
    except KeyboardInterrupt:
        logger.info("🛑 Capture interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"💥 Capture failed: {e}")
        return 1
    finally:
        logger.info("🔄 Stopping stream...")
        stream_handler.stop_stream()
        if cap:
            cap.release()
        logger.info("✅ Cleanup complete")
    
    return 0

if __name__ == "__main__":
    exit(main())
