import sys
import os
import re
from datetime import datetime, timedelta
from src.processing.rolling_buffer import RollingBuffer
import subprocess

rolling_buffer = RollingBuffer()
max_duration = rolling_buffer.buffer_duration

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
    print("Usage: python scripts/extract_clip.py <start_time:YYYY-MM-DDTHH:MM:SS> [duration_in_seconds]")
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

if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        usage()
    try:
        orig_start_time = datetime.strptime(sys.argv[1], "%Y-%m-%dT%H:%M:%S")
    except Exception:
        print("Invalid start_time format. Use YYYY-MM-DDTHH:MM:SS")
        usage()
    if len(sys.argv) == 3:
        try:
            duration_seconds = int(sys.argv[2])
        except Exception:
            print("Invalid duration. Please provide an integer number of seconds.")
            usage()
    else:
        duration_seconds = 10
    if duration_seconds > max_duration:
        print(f"Error: Requested duration ({duration_seconds}s) exceeds buffer maximum ({max_duration}s).")
        sys.exit(1)

    # Gather all available segment start times
    segment_tuples = [
        (datetime.strptime(filename[len("segment_"):-len(".mp4")], "%Y%m%d_%H%M%S"),
         os.path.join(rolling_buffer.buffer_dir, filename))
        for filename in rolling_buffer._list_segments()
        if filename.startswith("segment_") and filename.endswith(".mp4")
    ]
    segment_tuples.sort()
    # Try to find the latest available segment <= requested start time
    start_time = orig_start_time
    segment_start_set = {t[0] for t in segment_tuples}
    if start_time not in segment_start_set:
        # Only build a sorted list if we need to step back
        sorted_starts = [t[0] for t in segment_tuples]
        while start_time not in segment_start_set and start_time >= sorted_starts[0]:
            start_time -= timedelta(seconds=rolling_buffer.segment_duration)
        if start_time < sorted_starts[0]:
            print_buffer_window()
            print_available_segments(segment_tuples)
            print(f"Error: No available segment at or before requested start time ({orig_start_time.strftime('%Y-%m-%dT%H:%M:%S')}).")
            sys.exit(2)
        print(f"⚠️  Requested start time {orig_start_time.strftime('%Y-%m-%dT%H:%M:%S')} not available. Using closest earlier segment: {start_time.strftime('%Y-%m-%dT%H:%M:%S')}")

    end_time = start_time + timedelta(seconds=duration_seconds)
    needed_segments = [
        (segment_start_time, segment_path) for segment_start_time, segment_path in segment_tuples
        if segment_start_time + timedelta(seconds=rolling_buffer.segment_duration) > start_time and segment_start_time < end_time
    ]
    if not needed_segments:
        print_buffer_window()
        print_available_segments(segment_tuples)
        print("Error: Requested time is not in buffer window.")
        sys.exit(2)
    needed_segments.sort()
    first_needed_start = needed_segments[0][0]
    last_needed_end = needed_segments[-1][0] + timedelta(seconds=rolling_buffer.segment_duration)
    if first_needed_start > start_time or last_needed_end < end_time:
        print_buffer_window()
        print_available_segments(segment_tuples)
        print("Error: Requested time is not fully covered by buffer window.")
        sys.exit(2)
    output_path = f"clip_{start_time.strftime('%Y%m%d_%H%M%S')}_{duration_seconds}s.mp4"
    result_path = rolling_buffer.extract_clip(start_time, duration=duration_seconds, output_path=output_path)
    if not os.path.exists(result_path) or os.path.getsize(result_path) < 1024:
        print("Error: Extracted clip is empty or too small. Likely requested time is not in buffer window.")
        sys.exit(2)
    print(f"Clip extracted to {result_path}")
    gcs_url = upload_to_gcs(result_path, "caprid-videos-demo", f"buffer-captures/{os.path.basename(result_path)}")
    print(f"✅ Uploaded to {gcs_url}")