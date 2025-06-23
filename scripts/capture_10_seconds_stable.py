# scripts/capture_10_seconds_stable.py
"""
Capture exactly 10 seconds of video with optimized settings for stability
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

def main():
    # Suppress codec error messages
    suppress_ffmpeg_logs()
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    print("📹 Starting 10-second video capture (stable mode - main stream optimized)...")
    
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
    
    # Use main stream but with optimized settings for stability
    logger.info("🎥 Using main stream with stability optimizations...")
    
    cap = client.get_video_stream(config['reolink']['channel'])
    if not cap:
        logger.error("❌ Failed to get video stream")
        return 1
    
    # Apply stability optimizations
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)  # Small buffer but not 1
    cap.set(cv2.CAP_PROP_FPS, 10)        # Limit to 10 FPS for stability
    
    try:
        # Get video properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        logger.info(f"📺 Stream properties: {width}x{height}")
        
        # Test frame reading first
        logger.info("🔍 Testing frame capture...")
        test_frames = 0
        for i in range(10):
            ret, frame = cap.read()
            if ret and frame is not None:
                test_frames += 1
        
        if test_frames < 5:
            logger.error(f"❌ Stream too unreliable - only got {test_frames}/10 test frames")
            return 1
        
        logger.info(f"✅ Stream test passed - {test_frames}/10 frames captured")
        
        # Generate filename with timestamp
        now = datetime.now()
        filename = f"capture_{now.strftime('%Y%m%d_%H%M%S')}_10sec_stable.mp4"
        output_path = f"./output/segments/{filename}"
        
        # Use conservative FPS for encoding
        encoding_fps = 8.0  # Conservative but should work for most streams
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, encoding_fps, (width, height))
        
        if not out.isOpened():
            logger.error("❌ Failed to create video writer")
            return 1
        
        logger.info(f"📹 Recording 10 seconds to: {filename}")
        logger.info(f"🎬 Using encoding FPS: {encoding_fps}")
        logger.info(f"⏱️  Start: {now.strftime('%H:%M:%S')}")
        
        # Record for exactly 10 seconds with aggressive frame capture
        recording_start = time.time()
        recording_duration = 10.0
        frames_written = 0
        frames_attempted = 0
        last_progress_update = 0
        
        print("🔴 Recording in progress...")
        
        while True:
            current_time = time.time()
            elapsed = current_time - recording_start
            
            # Check if we've recorded for 10 seconds
            if elapsed >= recording_duration:
                print(f"\n⏱️  10 seconds completed! ({frames_written} frames captured)")
                break
            
            frames_attempted += 1
            
            # Try to read a frame
            ret, frame = cap.read()
            if ret and frame is not None:
                # Write frame to video
                out.write(frame)
                frames_written += 1
                
                # Small delay to prevent overwhelming the stream
                time.sleep(0.01)  # 10ms delay
            else:
                # If frame read fails, smaller delay and continue
                time.sleep(0.05)  # 50ms delay
                if frames_attempted % 20 == 0:  # Log every 20 failed attempts
                    logger.debug(f"Frame read issues at {elapsed:.1f}s (success rate: {frames_written/frames_attempted*100:.1f}%)")
            
            # Show progress every second
            if int(elapsed) > last_progress_update:
                remaining = max(0, recording_duration - elapsed)
                progress = (elapsed / recording_duration) * 100
                success_rate = frames_written / max(1, frames_attempted) * 100
                print(f"⏱️  {remaining:.1f}s remaining ({progress:.0f}%) - {frames_written} frames ({success_rate:.0f}% success)", end='\r')
                last_progress_update = int(elapsed)
        
        # Cleanup
        out.release()
        actual_duration = time.time() - recording_start
        success_rate = frames_written / max(1, frames_attempted) * 100
        
        logger.info(f"✅ Recording completed!")
        logger.info(f"📁 File saved: {output_path}")
        logger.info(f"⏱️  Recording duration: {actual_duration:.1f} seconds")
        logger.info(f"🎬 Frames captured: {frames_written} (attempted: {frames_attempted})")
        logger.info(f"📈 Success rate: {success_rate:.1f}%")
        
        if frames_written > 0:
            effective_fps = frames_written / actual_duration
            logger.info(f"📊 Effective FPS: {effective_fps:.1f}")
        
        # Check file size
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            logger.info(f"📦 File size: {file_size:.1f} MB")
            
            if file_size < 0.1:  # Less than 100KB
                logger.warning("⚠️ Video file is very small - may indicate recording issues")
                logger.info(f"💡 Try 'make capture' for the standard recording method")
                return 1
            elif frames_written < 30:  # Very few frames
                logger.warning("⚠️ Very few frames captured - stream may be unstable")
                logger.info(f"💡 Try 'make capture' for the standard recording method")
                return 1
            else:
                logger.info(f"✅ Recording appears successful!")
        else:
            logger.error("❌ File not found after recording")
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