import sys
import os
import time
from datetime import datetime, timedelta
from processing.rolling_buffer import RollingBuffer
import subprocess

rolling_buffer = RollingBuffer()
max_duration = rolling_buffer.max_seconds

def upload_to_gcs(local_path, bucket_name, destination_blob_name):
    """Upload a file to Google Cloud Storage using gcloud CLI"""
    gcs_uri = f"gs://{bucket_name}/{destination_blob_name}"
    result = subprocess.run(
        ["gcloud", "storage", "cp", local_path, gcs_uri],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"gcloud upload failed: {result.stderr}")
        sys.exit(2)
    return gcs_uri

def usage():
    print("Usage: python scripts/extract_clip.py <center_time:YYYY-MM-DDTHH:MM:SS> [duration_in_seconds]")
    print("The provided time will be the center of the clip.")
    print(f"Note: Maximum extractable duration is {max_duration//60} minutes ({max_duration} seconds).")
    sys.exit(1)

def print_buffer_window():
    segment_files = rolling_buffer._list_segments()
    if segment_files:
        first_segment = segment_files[0][len("segment_"):-len(".mp4")]
        last_segment = segment_files[-1][len("segment_"):-len(".mp4")]
        print(f"Available buffer window: {first_segment} to {last_segment}")

def print_available_segments(segment_tuples):
    print("Available segment start times in buffer:")
    for segment_start_time, segment_path in segment_tuples:
        print(f"  {segment_start_time.strftime('%Y-%m-%dT%H:%M:%S')}  ({os.path.basename(segment_path)})")

def wait_for_future_segments(needed_end_time, timeout=10):
    """Wait for segments to be recorded up to the needed end time."""
    print(f"Waiting for future segments up to {needed_end_time.strftime('%Y-%m-%dT%H:%M:%S')}...")
    start_wait = datetime.now()
    while datetime.now() < needed_end_time + timedelta(seconds=1):  # Add 1 second buffer
        if (datetime.now() - start_wait).total_seconds() > timeout:
            print("Timeout waiting for future segments")
            return False
        # Check if we have segments up to the needed time
        segment_tuples = [(
            datetime.strptime(filename[len("segment_"):-len(".mp4")], "%Y%m%d_%H%M%S"),
            os.path.join(rolling_buffer.buffer_dir, filename)
        ) for filename in rolling_buffer._list_segments()]
        if segment_tuples:
            latest_segment = max(t[0] for t in segment_tuples)
            if latest_segment >= needed_end_time:
                return True
        time.sleep(0.5)
    return False

if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        usage()
    try:
        center_time = datetime.strptime(sys.argv[1], "%Y-%m-%dT%H:%M:%S")
    except Exception:
        print("Invalid center_time format. Use YYYY-MM-DDTHH:MM:SS")
        usage()
    
    # Duration is always 10 seconds (5 before + 5 after)
    duration_seconds = 10
    half_duration = duration_seconds // 2

    # Calculate start and end times
    start_time = center_time - timedelta(seconds=half_duration)
    end_time = center_time + timedelta(seconds=half_duration)

    # If end_time is in the future, we need to wait
    now = datetime.now()
    if end_time > now:
        if not wait_for_future_segments(end_time):
            print("Failed to get future segments")
            sys.exit(1)

    # Gather all available segment start times
    segment_tuples = [
        (datetime.strptime(filename[len("segment_"):-len(".mp4")], "%Y%m%d_%H%M%S"),
         os.path.join(rolling_buffer.buffer_dir, filename))
        for filename in rolling_buffer._list_segments()
        if filename.startswith("segment_") and filename.endswith(".mp4")
    ]
    segment_tuples.sort()

    # Check if we have segments covering our time window
    if not segment_tuples:
        print("Error: No segments found in buffer. The buffer is empty.")
        print_buffer_window()
        sys.exit(2)

    # Find needed segments
    needed_segments = [
        (segment_start_time, segment_path) for segment_start_time, segment_path in segment_tuples
        if segment_start_time + timedelta(seconds=rolling_buffer.segment_duration) > start_time and segment_start_time < end_time
    ]
    
    if not needed_segments:
        print_buffer_window()
        print_available_segments(segment_tuples)
        print("Error: Requested time window is not in buffer window.")
        sys.exit(2)
    
    needed_segments.sort()
    first_needed_start = needed_segments[0][0]
    last_needed_end = needed_segments[-1][0] + timedelta(seconds=rolling_buffer.segment_duration)
    
    if first_needed_start > start_time or last_needed_end < end_time:
        print_buffer_window()
        print_available_segments(segment_tuples)
        print("Error: Requested time window is not fully covered by buffer window.")
        sys.exit(2)
    output_path = f"clip_{center_time.strftime('%Y%m%d_%H%M%S')}_{duration_seconds}s.mp4"
    result_path = rolling_buffer.extract_clip(start_time, duration=duration_seconds, output_path=output_path)
    
    if not os.path.exists(result_path) or os.path.getsize(result_path) < 1024:
        print("Error: Extracted clip is empty or too small. Likely requested time is not in buffer window.")
        sys.exit(2)
        
    print(f"Clip extracted to {result_path}")
    bucket_name = os.environ.get('GCS_BUCKET_NAME', 'caprid-videos-demo')
    project = os.environ.get('GOOGLE_CLOUD_PROJECT', 'pickle-devops-dev')
    os.environ['GOOGLE_CLOUD_PROJECT'] = project  # Ensure gcloud uses the right project
    
    print(f"Using GCS bucket: {bucket_name} in project: {project}")
    gcs_url = upload_to_gcs(result_path, bucket_name, f"buffer-captures/{os.path.basename(result_path)}")
    print(f"✅ Uploaded to {gcs_url}")