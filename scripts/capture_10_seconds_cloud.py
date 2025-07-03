"""
Capture exactly 10 seconds of video, then upload to a Google Cloud Storage bucket.
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

def flush_buffer(cap, flush_frames=10):
    """Flush old frames from the buffer to get real-time frames"""
    for _ in range(flush_frames):
        ret, frame = cap.read()
        if not ret:
            break
    return ret, frame if ret else (False, None)

def upload_to_gcs(local_path, bucket_name, destination_blob_name):
    """Upload a file to Google Cloud Storage"""
    from google.cloud import storage
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(local_path)
    return f"gs://{bucket_name}/{destination_blob_name}"

def main():
    # Suppress codec error messages
    suppress_ffmpeg_logs()

    setup_logging()
    logger = logging.getLogger(__name__)

    print("📹 Starting 10-second video capture (cloud upload mode)...")

    # Load configuration
    settings = Settings()
    config = settings.config

    # Initialize Reolink client
    client = ReolinkClient(
        host=config['reolink'].get('hostname') or config['reolink']['host'],
        username=config['reolink']['username'],
        password=config['reolink']['password'],
        port=config['reolink']['port']
    )

    # Authenticate
    if not client.authenticate():
        logger.error("❌ Failed to authenticate with camera")
        return 1

    # Use main stream for cloud capture
    logger.info("🎥 Using main stream for cloud capture...")

    cap = client.get_video_stream(config['reolink']['channel'])
    if not cap:
        logger.error("❌ Failed to get video stream")
        return 1

    # Apply real-time optimizations
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FPS, 15)

    # Additional real-time settings
    try:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('H','2','6','4'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    except:
        pass

    try:
        # Get video properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        logger.info(f"📺 Stream properties: {width}x{height}")

        # Flush any existing buffer to start fresh
        logger.info("🔄 Flushing stream buffer...")
        flush_buffer(cap, 15)

        # Test frame reading and measure actual capture rate with motion consideration
        logger.info("🔍 Testing frame capture rate...")
        test_start = time.time()
        test_frames = 0
        consecutive_failures = 0

        for i in range(30):  # Test for more frames to get better average
            ret, frame = cap.read()
            if ret and frame is not None:
                test_frames += 1
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if consecutive_failures > 5:
                    logger.warning("Too many consecutive frame failures during test")
                    break
            # No artificial delay - capture as fast as possible during test

        test_duration = time.time() - test_start

        if test_frames < 15:
            logger.error(f"❌ Stream too unreliable - only got {test_frames}/30 test frames")
            return 1

        # Calculate actual capture rate
        measured_fps = test_frames / test_duration
        # Use a conservative encoding rate that should work with motion
        encoding_fps = min(15.0, max(8.0, round(measured_fps * 0.8, 1)))

        logger.info(f"✅ Stream test passed - {test_frames}/30 frames captured")
        logger.info(f"📊 Measured capture rate: {measured_fps:.1f} FPS")
        logger.info(f"🎬 Will encode at: {encoding_fps} FPS (conservative for motion)")

        # Generate filename with timestamp
        now = datetime.now()
        filename = f"capture_{now.strftime('%Y%m%d_%H%M%S')}_10sec_cloud.mp4"
        output_path = f"./output/segments/{filename}"

        # Create video writer with conservative FPS
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, encoding_fps, (width, height))

        if not out.isOpened():
            logger.error("❌ Failed to create video writer")
            return 1

        logger.info(f"📹 Recording 10 seconds to: {filename}")
        logger.info(f"⏱️  Start: {now.strftime('%H:%M:%S')}")

        # Flush buffer again right before recording to ensure real-time start
        logger.info("🔄 Final buffer flush before recording...")
        flush_buffer(cap, 10)

        # Record for exactly 10 seconds with real-time frame capture
        recording_start = time.time()
        recording_duration = 10.0
        frames_written = 0
        frames_attempted = 0
        last_progress_update = 0
        last_flush_time = recording_start

        print("🔴 Recording in progress (cloud mode)...")

        while True:
            current_time = time.time()
            elapsed = current_time - recording_start

            # Check if we've recorded for 10 seconds
            if elapsed >= recording_duration:
                print(f"\n⏱️  10 seconds completed! ({frames_written} frames captured)")
                break

            # Periodically flush buffer to prevent lag buildup during motion
            if current_time - last_flush_time > 2.0:  # Every 2 seconds
                # Quick mini-flush (just 2-3 frames) to stay current
                for _ in range(3):
                    cap.read()
                last_flush_time = current_time
                logger.debug(f"Buffer mini-flush at {elapsed:.1f}s")

            frames_attempted += 1

            # Try to read a frame
            ret, frame = cap.read()
            if ret and frame is not None:
                # Write frame to video
                out.write(frame)
                frames_written += 1
                
                # Minimal delay to prevent overwhelming but maintain real-time
                time.sleep(0.01)  # 10ms
            else:
                # If frame read fails, very short delay
                time.sleep(0.02)  # 20ms delay

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
        logger.info(f"🎥 Expected video duration: ~{frames_written / encoding_fps:.1f} seconds")

        if frames_written > 0:
            effective_fps = frames_written / actual_duration
            logger.info(f"📊 Effective capture FPS: {effective_fps:.1f}")

        # Check file size and duration
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            logger.info(f"📦 File size: {file_size:.1f} MB")

            expected_duration = frames_written / encoding_fps

            if file_size < 0.1:
                logger.warning("⚠️ Video file is very small - may indicate recording issues")
                return 1
            elif frames_written < 30:
                logger.warning("⚠️ Very few frames captured - stream may be unstable")
                return 1
            elif expected_duration < 8.0:
                logger.warning(f"⚠️ Video duration shorter than expected ({expected_duration:.1f}s)")
                logger.info("💡 This may indicate buffer lag issues during motion")
                logger.info("🎬 Video should still contain 10 seconds of real-time content")
            else:
                logger.info(f"✅ Recording successful! Duration: {expected_duration:.1f}s")
        else:
            logger.error("❌ File not found after recording")
            return 1

        # --- Google Cloud Storage upload section ---
        bucket_name = os.environ.get("GCS_BUCKET_NAME")
        if not bucket_name:
            logger.error("❌ GCS_BUCKET_NAME environment variable not set.")
            return 1
        # bucket_name = "caprid-videos-demo"

        destination_blob_name = f"captures/{filename}"
        logger.info(f"☁️ Uploading to GCS bucket: {bucket_name} as {destination_blob_name}")
        gcs_url = upload_to_gcs(output_path, bucket_name, destination_blob_name)
        logger.info(f"✅ Uploaded to {gcs_url}")

        # --- Delete local file after upload ---
        logger.info(f"🗑️ Deleting local file: {output_path}")
        os.remove(output_path)

        logger.info("🎉 Cloud capture complete.")

    except KeyboardInterrupt:
        logger.info("🛑 Capture interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"💥 Capture or upload failed: {e}")
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