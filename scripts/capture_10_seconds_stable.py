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

def measure_actual_fps(cap, sample_frames=30, max_time=5.0):
    """Measure the actual frame rate by timing frame delivery"""
    logger = logging.getLogger(__name__)
    logger.info("📊 Measuring actual stream frame rate...")
    
    start_time = time.time()
    frames_received = 0
    
    for i in range(sample_frames):
        frame_start = time.time()
        ret, frame = cap.read()
        
        if ret and frame is not None:
            frames_received += 1
        
        # Safety check - don't spend more than max_time measuring
        if time.time() - start_time > max_time:
            logger.info(f"⏱️ Measurement timeout after {max_time}s")
            break
            
        # Small delay if frame read fails
        if not ret:
            time.sleep(0.1)
    
    elapsed_time = time.time() - start_time
    
    if frames_received > 0 and elapsed_time > 0:
        actual_fps = frames_received / elapsed_time
        logger.info(f"📈 Measured FPS: {actual_fps:.2f} ({frames_received} frames in {elapsed_time:.2f}s)")
        return max(1.0, round(actual_fps, 1))  # Minimum 1 FPS
    else:
        logger.warning("⚠️ Could not measure FPS, using default")
        return 6.0  # Conservative default for sub-stream

def main():
    # Suppress codec error messages
    suppress_ffmpeg_logs()
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    print("📹 Starting 10-second video capture (stable mode with time-based recording)...")
    
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
        
        # Record for exactly 10 seconds using TIME-BASED approach
        recording_start = time.time()
        recording_duration = 10.0  # 10 seconds
        frames_written = 0
        last_progress_update = 0
        
        print("🔴 Recording in progress...")
        
        while True:
            current_time = time.time()
            elapsed = current_time - recording_start
            
            # Check if we've recorded for 10 seconds
            if elapsed >= recording_duration:
                print("\n⏱️  10 seconds completed!")
                break
            
            # Try to read a frame with timeout
            ret, frame = cap.read()
            if ret and frame is not None:
                # Write frame to video
                out.write(frame)
                frames_written += 1
            else:
                # If frame read fails, wait a bit but don't stop recording
                logger.debug(f"Frame read failed at {elapsed:.1f}s, continuing...")
                time.sleep(0.05)  # 50ms delay
            
            # Show progress every second
            if int(elapsed) > last_progress_update:
                remaining = max(0, recording_duration - elapsed)
                progress = (elapsed / recording_duration) * 100
                print(f"⏱️  {remaining:.1f}s remaining ({progress:.0f}%)...", end='\r')
                last_progress_update = int(elapsed)
            
            # Safety timeout - force exit after 12 seconds
            if elapsed > 12.0:
                logger.warning("⚠️ Safety timeout reached, stopping recording")
                break
        
        # Cleanup
        out.release()
        actual_duration = time.time() - recording_start
        
        logger.info(f"✅ Video captured successfully!")
        logger.info(f"📁 File saved: {output_path}")
        logger.info(f"⏱️  Recording duration: {actual_duration:.1f} seconds")
        logger.info(f"🎬 Frames captured: {frames_written}")
        
        if frames_written > 0:
            effective_fps = frames_written / actual_duration
            logger.info(f"📈 Effective FPS: {effective_fps:.1f}")
        
        # Check file size
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            logger.info(f"📊 File size: {file_size:.1f} MB")
            
            if file_size < 0.1:  # Less than 100KB probably means empty file
                logger.warning("⚠️ Video file seems unusually small - check for recording issues")
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
