import sys
from datetime import datetime, timedelta
from src.processing.rolling_buffer import RollingBuffer
import os
import re

buffer = RollingBuffer()
max_duration = buffer.buffer_duration

def upload_to_gcs(local_path, bucket_name, destination_blob_name):
    from google.cloud import storage
    client = storage.Client(project="pickle-devops-dev")
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(local_path)
    return f"gs://{bucket_name}/{destination_blob_name}"

def usage():
    print("Usage: python scripts/extract_clip.py <start_time:YYYY-MM-DDTHH:MM:SS> [duration (e.g. 10s, 3m, 2h)]")
    print(f"Note: Maximum extractable duration is {max_duration//60} minutes ({max_duration} seconds).")
    sys.exit(1)

def parse_duration(duration_str):
    if duration_str is None:
        return 10  # default to 10 seconds
    match = re.match(r'^(\d+)([smh]?)$', duration_str.strip().lower())
    if not match:
        print("Invalid duration format. Use a number optionally followed by s (seconds), m (minutes), or h (hours).")
        usage()
    value, unit = match.groups()
    value = int(value)
    if unit == 'm':
        return value * 60
    elif unit == 'h':
        return value * 3600
    else:  # default or 's'
        return value

if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        usage()
    start_time_str = sys.argv[1]
    duration = 10
    if len(sys.argv) == 3:
        duration = parse_duration(sys.argv[2])
    if duration > max_duration:
        print(f"Error: Requested duration ({duration}s) exceeds buffer maximum ({max_duration}s).")
        sys.exit(1)
    try:
        start_dt = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%S")
    except Exception:
        print("Invalid start_time format. Use YYYY-MM-DDTHH:MM:SS")
        usage()

    output_path = f"clip_{start_dt.strftime('%Y%m%d_%H%M%S')}_{duration}s.mp4"

    try:
        # Find all segments that overlap with the requested window
        end_dt = start_dt + timedelta(seconds=duration)
        needed_segments = []
        for fname in buffer._list_segments():
            ts_str = fname[len("segment_"):-len(".mp4")]
            try:
                seg_start = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
                seg_end = seg_start + timedelta(seconds=buffer.segment_duration)
                if seg_end > start_dt and seg_start < end_dt:
                    seg_path = os.path.join(buffer.buffer_dir, fname)
                    needed_segments.append((seg_start, seg_path))
            except Exception:
                continue

        # Check if the needed segments fully cover the requested window
        if not needed_segments:
            segments = buffer._list_segments()
            if segments:
                first = segments[0][len("segment_"):-len(".mp4")]
                last = segments[-1][len("segment_"):-len(".mp4")]
                print(f"Available buffer window: {first} to {last}")
            print("Error: Requested time is not in buffer window.")
            sys.exit(2)

        # Check that the first segment starts before or at start_dt and the last segment ends after or at end_dt
        needed_segments.sort()
        first_seg_start = needed_segments[0][0]
        last_seg_end = needed_segments[-1][0] + timedelta(seconds=buffer.segment_duration)
        if first_seg_start > start_dt or last_seg_end < end_dt:
            segments = buffer._list_segments()
            if segments:
                first = segments[0][len("segment_"):-len(".mp4")]
                last = segments[-1][len("segment_"):-len(".mp4")]
                print(f"Available buffer window: {first} to {last}")
            print("Error: Requested time is not fully covered by buffer window.")
            sys.exit(2)

        # Only pass the segment paths to extract_clip
        segment_paths = [seg_path for _, seg_path in needed_segments]
        result = buffer.extract_clip(start_dt, duration=duration, output_path=output_path)

        # Check output file size
        if not os.path.exists(result) or os.path.getsize(result) < 1024:
            print("Error: Extracted clip is empty or too small. Likely requested time is not in buffer window.")
            sys.exit(2)

        print(f"Clip extracted to {result}")
        # Upload to GCS
        bucket_name = "caprid-videos-demo"
        destination_blob_name = f"buffer-captures/{os.path.basename(result)}"
        gcs_url = upload_to_gcs(result, bucket_name, destination_blob_name)
        print(f"✅ Uploaded to {gcs_url}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(2)