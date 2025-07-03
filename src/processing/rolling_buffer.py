import os
import cv2
import time
import subprocess
from datetime import datetime, timedelta
from src.stream.reolink_client import ReolinkClient
from src.config.settings import Settings

class RollingBuffer:
    def __init__(self, buffer_dir="./rolling_buffer", segment_duration=1, buffer_minutes=10):
        self.buffer_dir = buffer_dir
        self.segment_duration = segment_duration  # seconds
        self.buffer_minutes = buffer_minutes
        os.makedirs(self.buffer_dir, exist_ok=True)

    def _segment_filename(self, dt):
        return os.path.join(self.buffer_dir, f"segment_{dt.strftime('%Y%m%d_%H%M%S')}.mp4")

    def _list_segments(self):
        files = [f for f in os.listdir(self.buffer_dir) if f.startswith("segment_") and f.endswith(".mp4")]
        files.sort()
        return files

    def _cleanup_old_segments(self):
        now = datetime.now()
        cutoff = now - timedelta(minutes=self.buffer_minutes)
        for fname in self._list_segments():
            ts_str = fname[len("segment_"):-len(".mp4")]
            try:
                ts = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
                if ts < cutoff:
                    os.remove(os.path.join(self.buffer_dir, fname))
            except Exception:
                continue

    def start_recording(self):
        """Continuously records 1s segments from the Reolink stream."""
        settings = Settings()
        config = settings.config
        client = ReolinkClient(
            host=config['reolink'].get('hostname') or config['reolink']['host'],
            username=config['reolink']['username'],
            password=config['reolink']['password'],
            port=config['reolink']['port']
        )
        if not client.authenticate():
            raise RuntimeError("Failed to authenticate with camera")
        cap = client.get_video_stream(config['reolink']['channel'])
        if not cap:
            raise RuntimeError("Failed to get video stream")

        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 15
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        print(f"Rolling buffer started: {self.buffer_minutes} min, {self.segment_duration}s segments, {fps} FPS")
        try:
            while True:
                start_time = datetime.now()
                fname = self._segment_filename(start_time)
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(fname, fourcc, fps, (width, height))
                frames_to_write = int(fps * self.segment_duration)
                for _ in range(frames_to_write):
                    ret, frame = cap.read()
                    if not ret:
                        break
                    out.write(frame)
                out.release()
                self._cleanup_old_segments()
                # Sleep to align with real time
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed < self.segment_duration:
                    time.sleep(self.segment_duration - elapsed)
        finally:
            cap.release()

    def extract_clip(self, start_dt, duration=10, output_path="output_clip.mp4"):
        """
        Extracts a clip starting at start_dt (datetime) for 'duration' seconds.
        Returns the path to the output file, or raises if not enough data.
        """
        # Find all segments that overlap with the requested window
        end_dt = start_dt + timedelta(seconds=duration)
        needed_segments = []
        for fname in self._list_segments():
            ts_str = fname[len("segment_"):-len(".mp4")]
            try:
                seg_start = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
                seg_end = seg_start + timedelta(seconds=self.segment_duration)
                # If segment overlaps with requested window, include it
                if seg_end > start_dt and seg_start < end_dt:
                    needed_segments.append(os.path.join(self.buffer_dir, fname))
            except Exception:
                continue

        if not needed_segments or (needed_segments[0] > end_dt.strftime("%Y%m%d_%H%M%S")):
            raise RuntimeError("Requested time is not in buffer window.")

        # Write ffmpeg concat file
        concat_list_path = os.path.join(self.buffer_dir, "segments_to_concat.txt")
        with open(concat_list_path, "w") as f:
            for seg in needed_segments:
                f.write(f"file '{os.path.abspath(seg)}'\n")

        # Use ffmpeg to concatenate
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list_path,
            "-ss", str((start_dt - datetime.strptime(
                os.path.basename(needed_segments[0])[8:-4], "%Y%m%d_%H%M%S"
            )).total_seconds()),
            "-t", str(duration),
            "-c", "copy", output_path
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr.decode()}")
        return output_path

# Example usage:
# from src.processing.rolling_buffer import RollingBuffer
# buffer = RollingBuffer()
# buffer.start_recording()  # Run in a background process/thread
# # To extract a clip:
# dt = datetime.now() - timedelta(seconds=30)  # 30 seconds ago
# buffer.extract_clip(dt, duration=10, output_path="clip.mp4")