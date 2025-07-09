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
    print("Usage: python scripts/extract_clip.py <start_time:YYYY-MM-DDTHH:MM:SS>")
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        usage()
    start_time_str = sys.argv[1]
    duration = 10
    try:
        start_dt = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%S")
    except Exception:
        print("Invalid start_time format. Use YYYY-MM-DDTHH:MM:SS")
        usage()

    output_path = f"clip_{start_dt.strftime('%Y%m%d_%H%M%S')}_{duration}s.mp4"

    buffer = RollingBuffer()
    try:
        result = buffer.extract_clip(start_dt, duration=duration, output_path=output_path)
        print(f"Clip extracted to {result}")
        # Upload to GCS
        bucket_name = "caprid-videos-demo"
        destination_blob_name = f"buffer-captures/{os.path.basename(result)}"
        gcs_url = upload_to_gcs(result, bucket_name, destination_blob_name)
        print(f"✅ Uploaded to {gcs_url}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(2)