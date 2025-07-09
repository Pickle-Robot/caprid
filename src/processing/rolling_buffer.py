import os
import cv2
import time
import subprocess
from datetime import datetime, timedelta
from src.stream.reolink_client import ReolinkClient
from src.config.settings import Settings

class RollingBuffer:
    def __init__(self, buffer_dir="output/segments", segment_duration=1, buffer_duration=600):
        """
        Args:
            buffer_dir (str): Directory where segments are stored.
            segment_duration (int): Duration of each segment in seconds.
            buffer_duration (int): Total buffer duration in seconds.
        """
        self.buffer_dir = buffer_dir
        self.segment_duration = segment_duration
        self.buffer_duration = buffer_duration
        os.makedirs(self.buffer_dir, exist_ok=True)

    def _list_segments(self):
        """Return a sorted list of segment filenames."""
        files = [f for f in os.listdir(self.buffer_dir) if f.startswith("segment_") and f.endswith(".mp4")]
        files.sort()
        return files

    def get_segment_times(self):
        """Return a list of (start_time: datetime, filename) tuples for all segments."""
        segment_files = self._list_segments()
        return [
            (datetime.strptime(f[len("segment_"):-len(".mp4")], "%Y%m%d_%H%M%S"), f)
            for f in segment_files
        ]

    def extract_clip(self, start_time, duration, output_path):
        """
        Extract a clip from the buffer.

        Args:
            start_time (datetime): Start time of the clip.
            duration (int): Duration of the clip in seconds.
            output_path (str): Path to save the extracted clip.

        Returns:
            str: Path to the extracted clip.
        """
        # Find all segments that overlap with the requested window
        end_time = start_time + timedelta(seconds=duration)
        needed_segments = []
        for fname in self._list_segments():
            ts_str = fname[len("segment_"):-len(".mp4")]
            try:
                seg_start = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
                seg_end = seg_start + timedelta(seconds=self.segment_duration)
                # If segment overlaps with requested window, include it
                if seg_end > start_time and seg_start < end_time:
                    needed_segments.append(os.path.join(self.buffer_dir, fname))
            except Exception:
                continue

        if not needed_segments or (needed_segments[0] > end_time.strftime("%Y%m%d_%H%M%S")):
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
            "-ss", str((start_time - datetime.strptime(
                os.path.basename(needed_segments[0])[8:-4], "%Y%m%d_%H%M%S"
            )).total_seconds()),
            "-t", str(duration),
            "-c", "copy", output_path
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr.decode()}")
        return output_path

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

        print(f"Rolling buffer started: {self.buffer_duration} sec, {self.segment_duration}s segments, {fps} FPS")
        try:
            while True:
                start_time = datetime.now()
                fname = os.path.join(self.buffer_dir, f"segment_{start_time.strftime('%Y%m%d_%H%M%S')}.mp4")
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(fname, fourcc, fps, (width, height))
                frames_to_write = int(fps * self.segment_duration)
                for _ in range(frames_to_write):
                    ret, frame = cap.read()
                    if not ret:
                        break
                    out.write(frame)
                out.release()
                # Sleep to align with real time
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed < self.segment_duration:
                    time.sleep(self.segment_duration - elapsed)
        finally:
            cap.release()

if __name__ == "__main__":
    RollingBuffer().start_recording()

# Example usage:
# from src.processing.rolling_buffer import RollingBuffer
# buffer = RollingBuffer()
# buffer.start_recording()  # Run in a background process/thread
# # To extract a clip:
# dt = datetime.now() - timedelta(seconds=30)  # 30 seconds ago
# buffer.extract_clip(dt, duration=10, output_path="clip.mp4")