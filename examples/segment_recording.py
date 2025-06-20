"""
Example of how to capture video segments using timestamps
"""

import time
from datetime import datetime, timedelta
from src.config.settings import Settings
from src.stream.reolink_client import ReolinkClient
from src.stream.stream_handler import StreamHandler

def main():
    # Initialize components
    settings = Settings()
    config = settings.config
    
    client = ReolinkClient(
        host=config['reolink']['host'],
        username=config['reolink']['username'],
        password=config['reolink']['password'],
        port=config['reolink']['port']
    )
    
    if not client.authenticate():
        print("Failed to authenticate")
        return
    
    cap = client.get_video_stream(config['reolink']['channel'])
    if not cap:
        print("Failed to get video stream")
        return
    
    # Create stream handler with 2-minute buffer for historical recording
    stream_handler = StreamHandler(cap, buffer_seconds=120)
    
    # Start the stream
    stream_thread = stream_handler.start_stream()
    
    # Wait for stream to initialize
    print("Initializing stream...")
    time.sleep(3)
    
    try:
        # Example 1: Record the last 30 seconds
        print("Recording segment: last 30 seconds")
        now = datetime.now()
        start_time = now - timedelta(seconds=30)
        end_time = now
        
        recording_id = stream_handler.start_segment_recording(
            start_time, 
            end_time, 
            "./output/segments/last_30_seconds.mp4"
        )
        
        # Example 2: Record multiple historical segments
        print("Recording multiple historical segments...")
        historical_timestamps = [
            (now - timedelta(seconds=60), now - timedelta(seconds=45)),  # 45-60 seconds ago
            (now - timedelta(seconds=40), now - timedelta(seconds=25)),  # 25-40 seconds ago
            (now - timedelta(seconds=20), now - timedelta(seconds=5)),   # 5-20 seconds ago
        ]
        
        recording_ids = stream_handler.record_segment_from_timestamps(
            historical_timestamps, 
            "./output/segments"
        )
        
        print(f"Completed {len(recording_ids)} historical recordings")
        
        # Example 3: Record based on events (simulate motion detection)
        print("Simulating event-based recording...")
        time.sleep(10)  # Wait a bit to accumulate some buffer
        
        # Simulate motion detected - record last 15 seconds
        motion_time = datetime.now()
        event_start = motion_time - timedelta(seconds=15)
        event_end = motion_time  # Up to now
        
        event_recording = stream_handler.start_segment_recording(
            event_start,
            event_end,
            f"./output/segments/motion_event_{motion_time.strftime('%Y%m%d_%H%M%S')}.mp4"
        )
        
        print(f"Motion event recording completed: {event_recording}")
        
        # Wait a bit more then stop
        print("Waiting before stopping...")
        time.sleep(10)
        
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        stream_handler.stop_stream()
        print("All recordings stopped")

if __name__ == "__main__":
    main()


# Usage examples for integration:

def record_segments_from_csv(csv_file: str, stream_handler: StreamHandler):
    """
    Example: Read timestamps from CSV and record segments
    CSV format: start_time,end_time
    2024-01-01 10:30:00,2024-01-01 10:30:30
    2024-01-01 11:15:00,2024-01-01 11:15:45
    """
    import csv
    from datetime import datetime
    
    timestamps = []
    with open(csv_file, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            start = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
            end = datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S')
            timestamps.append((start, end))
    
    return stream_handler.record_segment_from_timestamps(timestamps)

def record_segments_from_json(json_file: str, stream_handler: StreamHandler):
    """
    Example: Read timestamps from JSON
    {
        "segments": [
            {"start": "2024-01-01T10:30:00", "end": "2024-01-01T10:30:30"},
            {"start": "2024-01-01T11:15:00", "end": "2024-01-01T11:15:45"}
        ]
    }
    """
    import json
    from datetime import datetime
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    timestamps = []
    for segment in data['segments']:
        start = datetime.fromisoformat(segment['start'])
        end = datetime.fromisoformat(segment['end'])
        timestamps.append((start, end))
    
    return stream_handler.record_segment_from_timestamps(timestamps)