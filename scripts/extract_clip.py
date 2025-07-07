import sys
from datetime import datetime
from src.processing.rolling_buffer import RollingBuffer
import os

def upload_to_gcs(local_path, bucket_name, destination_blob_name):
    from google.cloud import storage
    client = storage.Client(project="pickle-devops-dev")
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(local_path)
    return f"gs://{bucket_name}/{destination_blob_name}"

def usage():
    print("Usage: python scripts/extract_clip.py <start_time:YYYY-MM-DDTHH:MM:SS> [duration_seconds] [output_path]")
    sys.exit(1)

if __name__ == "__main__":
    argc = len(sys.argv)
    if argc < 2 or argc > 4:
        usage()
    start_time_str = sys.argv[1]
    duration = 10
    output_path = None

    if argc >= 3:
        try:
            duration = int(sys.argv[2])
        except Exception:
            print("Invalid duration. Must be an integer (seconds).")
            usage()
    if argc == 4:
        output_path = sys.argv[3]

    try:
        start_dt = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%S")
    except Exception:
        print("Invalid start_time format. Use YYYY-MM-DDTHH:MM:SS")
        usage()

    if not output_path:
        output_path = f"clip_{start_dt.strftime('%Y%m%d_%H%M%S')}_{duration}s.mp4"

    buffer = RollingBuffer()
    try:
        result = buffer.extract_clip(start_dt, duration=duration, output_path=output_path)
        print(f"Clip extracted to {result}")
        # Upload to GCS
        bucket_name = "caprid-videos-demo"
        destination_blob_name = f"extracted/{os.path.basename(result)}"
        gcs_url = upload_to_gcs(result, bucket_name, destination_blob_name)
        print(f"✅ Uploaded to {gcs_url}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(2)