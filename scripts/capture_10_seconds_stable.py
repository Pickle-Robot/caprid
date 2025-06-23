"""
Capture exactly 10 seconds of video from the Reolink camera with error suppression and proper FPS detection
"""

import logging
import time
import os
import cv2
from datetime import datetime
from src.config.settings import Settings
from src.stream.reolink_client import ReolinkClient

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def suppress_ffmpeg_logs():
    """Suppress FFmpeg/OpenCV video codec error messages"""
    os.environ['OPENCV_FFMPEG_LOGLEVEL'] = '-8'  # Suppress all FFmpeg logs
    os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'     # Only show OpenCV errors

def measure_actual_fps(cap, sample_frames=30):
    """Measure the actual frame rate by timing frame delivery"""
    logger = logging.getLogger(__name__)
    logger.info("📊 Measuring actual stream frame rate...")
    
    start_time = time.time()
    frames_received = 0
    
    for i in range(sample_frames):
        ret, frame = cap.read()
        if ret and frame is not None:
            frames_received += 1
        else:
            # Small delay if frame read fails
            time.sleep(0.01)
    
    elapsed_time = time.time() - start_time
    
    if frames_received > 0 and elapsed_time > 0:
        actual_fps = frames_received / elapsed_time
        logger.info(f"📈 Measured FPS: {actual_fps:.2f} ({frames_received} frames in {elapsed_time:.2f}s)")
        return round(actual_fps, 1)
    else:
        logger.warning("⚠️ Could not measure FPS, using default")
        return 10.0  # Conservative default

def main():
    # Suppress codec error messages
    suppress_ffmpeg_logs()
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    print("📹 Starting 10-second video capture (stable mode with FPS detection)...")
    
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
    sub_stream_url = f"rtsp://{config['reolink']['username']}:{config['reolink']['password']}@{config['reolink']['host']}:554/h264Preview_01_sub"
    
    cap = cv2.VideoCapture(sub_stream_url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    stream_type = "sub-stream"
    if not cap.isOpened():
        logger.info("Sub-stream failed, trying main stream...")
        cap = client.get_video_stream(config['reolink']['channel'])
        stream_type = "main stream"
        if not cap:
            logger.error("❌ Failed to get video stream")
            return 1
    else:
        logger.info("✅ Using sub-stream for capture")
    
    try:
        # Get basic video properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        reported_fps = cap.get(cv2.CAP_PROP_FPS)
        
        logger.info(f"📺 Stream properties: {width}x{height}")
        logger.info(f"📊 Reported FPS: {reported_fps} (often inaccurate for RTSP)")
        
        # Wait for stream to stabilize
        logger.info("⏳ Allowing stream to stabilize...")
        time.sleep(2)
        
        # Measure actual FPS
        actual_fps = measure_actual_fps(cap)
        logger.info(f"✅ Using measured FPS: {actual_fps}")
        
        # Generate filename with timestamp
        now = datetime.now()
        filename = f"capture_{now.strftime('%Y%m%d_%H%M%S')}_10sec_stable.mp4"
        output_path = f"./output/segments/{filename}"
        
        # Create video writer with measured FPS
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, actual_fps, (width, height))
        
        if not out.isOpened():
            logger.error("❌ Failed to create video writer")
            return 1
        
        logger.info(f"📹 Recording 10 seconds to: {filename}")
        logger.info(f"🎬 Using {stream_type} at {actual_fps} FPS")
        logger.info(f"⏱️  Start: {now.strftime('%H:%M:%S')}")
        
        # Record for exactly 10 seconds based on actual FPS
        start_time = time.time()
        target_frames = int(actual_fps * 10)  # 10 seconds worth of frames at actual FPS
        frames_written = 0
        
        print("🔴 Recording in progress...")
        
        while frames_written < target_frames:
            ret, frame = cap.read()
            if not ret or frame is None:
                logger.warning(f"⚠️ Failed to read frame {frames_written + 1}, continuing...")
                # Small delay to prevent busy loop
                time.sleep(1.0 / actual_fps)
                continue
            
            # Write frame to video
            out.write(frame)
            frames_written += 1
            
            # Show progress
            elapsed = time.time() - start_time
            progress = (frames_written / target_frames) * 100
            remaining = max(0, 10 - elapsed)
            
            if frames_written % max(1, int(actual_fps)) == 0:  # Update every second
                print(f"⏱️  {remaining:.1f}s remaining ({progress:.0f}%)...", end='\r')
        
        print("⏱️  Recording complete!     ")
        
        # Cleanup
        out.release()
        elapsed_time = time.time() - start_time
        
        logger.info(f"✅ Video captured successfully!")
        logger.info(f"📁 File saved: {output_path}")
        logger.info(f"⏱️  Recording duration: {elapsed_time:.1f} seconds")
        logger.info(f"🎬 Frames captured: {frames_written}")
        logger.info(f"📈 Effective FPS: {frames_written / 10:.1f}")
        
        # Check file size
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            logger.info(f"📊 File size: {file_size:.1f} MB")
        else:
            logger.warning("⚠️ File not found after recording")
            return 1
        
    except KeyboardInterrupt:
        logger.info("🛑 Capture interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"💥 Capture failed: {e}")
        return 1
    finally:
        logger.info("🔄 Cleaning up...")
        if cap:
            cap.release()
        if 'out' in locals():
            out.release()
        logger.info("✅ Cleanup complete")
    
    return 0

if __name__ == "__main__":
    exit(main())
