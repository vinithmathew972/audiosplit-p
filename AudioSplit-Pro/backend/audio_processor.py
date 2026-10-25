import os
import json
import subprocess
import shutil
import time
import zipfile
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

# Supported audio and video extensions
SUPPORTED_AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".wma", ".aiff", ".aif", ".opus"
}
SUPPORTED_VIDEO_EXTENSIONS = {
    ".mp4", ".mov", ".mkv", ".avi", ".webm", ".mpeg", ".mpg"
}
ALL_SUPPORTED_EXTENSIONS = SUPPORTED_AUDIO_EXTENSIONS | SUPPORTED_VIDEO_EXTENSIONS

# Codec mappings for desired output formats
OUTPUT_FORMAT_SETTINGS = {
    "mp3": {
        "ext": ".mp3",
        "codec_args": ["-c:a", "libmp3lame", "-b:a", "320k", "-q:a", "0"],
        "mime": "audio/mpeg"
    },
    "wav": {
        "ext": ".wav",
        "codec_args": ["-c:a", "pcm_s16le"],
        "mime": "audio/wav"
    },
    "m4a": {
        "ext": ".m4a",
        "codec_args": ["-c:a", "aac", "-b:a", "256k"],
        "mime": "audio/mp4"
    },
    "aac": {
        "ext": ".aac",
        "codec_args": ["-c:a", "aac", "-b:a", "256k"],
        "mime": "audio/aac"
    },
    "flac": {
        "ext": ".flac",
        "codec_args": ["-c:a", "flac"],
        "mime": "audio/flac"
    },
    "ogg": {
        "ext": ".ogg",
        "codec_args": ["-c:a", "libvorbis", "-q:a", "6"],
        "mime": "audio/ogg"
    },
    "opus": {
        "ext": ".opus",
        "codec_args": ["-c:a", "libopus", "-b:a", "192k"],
        "mime": "audio/opus"
    },
    "wma": {
        "ext": ".wma",
        "codec_args": ["-c:a", "wmav2", "-b:a", "192k"],
        "mime": "audio/x-ms-wma"
    },
    "aiff": {
        "ext": ".aiff",
        "codec_args": ["-c:a", "pcm_s16be"],
        "mime": "audio/aiff"
    }
}

def format_duration(seconds: float) -> str:
    """Format duration in seconds to HH:MM:SS or MM:SS."""
    seconds = max(0.0, float(seconds))
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

def format_filesize(size_bytes: int) -> str:
    """Format byte count to readable string (KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def probe_media(file_path: Path) -> Dict[str, Any]:
    """Inspect media file using ffprobe and extract technical metadata.
    Returns a dictionary including audio codec info.
    """
    # Existing logic unchanged up to returning dict; no edit needed here.
    """Inspect media file using ffprobe and extract technical metadata."""
    if not file_path.exists():
        # Attempt to locate the file relative to the project root (useful for test files)
        project_root = Path(__file__).resolve().parent.parent
        alt_path = project_root / file_path
        if alt_path.exists():
            file_path = alt_path
        else:
            raise FileNotFoundError(f"File not found: {file_path}")

    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=format_name,duration,size,bit_rate,tags",
        "-show_streams",
        "-of", "json",
        str(file_path)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        probe_data = json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        stderr_msg = e.stderr.strip() if e.stderr else "Invalid or corrupted media file."
        raise ValueError(f"FFprobe inspection failed: {stderr_msg}")
    except json.JSONDecodeError:
        raise ValueError("Failed to parse media metadata from FFprobe.")

    format_info = probe_data.get("format", {})
    streams = probe_data.get("streams", [])

    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    video_streams = [s for s in streams if s.get("codec_type") == "video"]

    if not audio_streams:
        raise ValueError("The uploaded file does not contain an audio track. Please upload an audio or video file with sound.")

    first_audio = audio_streams[0]
    duration_str = format_info.get("duration") or first_audio.get("duration")
    if not duration_str:
        raise ValueError("Unable to determine media duration.")

    duration = float(duration_str)
    size_bytes = int(format_info.get("size") or file_path.stat().st_size)
    bit_rate = int(format_info.get("bit_rate") or first_audio.get("bit_rate") or 0)

    is_video = len(video_streams) > 0
    format_name = format_info.get("format_name", "unknown")

    return {
        "filename": file_path.name,
        "duration": duration,
        "duration_formatted": format_duration(duration),
        "size_bytes": size_bytes,
        "size_formatted": format_filesize(size_bytes),
        "bit_rate": bit_rate,
        "is_video": is_video,
        "format_name": format_name,
        "audio_codec": first_audio.get("codec_name", "unknown"),
        "sample_rate": first_audio.get("sample_rate", "unknown"),
        "channels": first_audio.get("channels", 2)
    }

def get_ffmpeg_capabilities() -> Dict[str, Any]:
    """Check FFmpeg version and supported audio encoders."""
    version_str = "Unknown"
    try:
        v_res = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=True)
        first_line = v_res.stdout.splitlines()[0] if v_res.stdout else "FFmpeg available"
        version_str = first_line
    except Exception as e:
        version_str = f"FFmpeg check error: {str(e)}"

    encoders = {}
    test_codecs = ["libmp3lame", "pcm_s16le", "aac", "flac", "libvorbis", "libopus", "wmav2"]
    try:
        enc_res = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True, check=True)
        stdout = enc_res.stdout
        for codec in test_codecs:
            encoders[codec] = codec in stdout
    except Exception:
        for codec in test_codecs:
            encoders[codec] = True

    return {
        "version": version_str,
        "encoders": encoders,
        "supported_audio_inputs": sorted(list(SUPPORTED_AUDIO_EXTENSIONS)),
        "supported_video_inputs": sorted(list(SUPPORTED_VIDEO_EXTENSIONS)),
        "supported_outputs": list(OUTPUT_FORMAT_SETTINGS.keys())
    }

class JobManager:
    """Thread-safe manager for audio splitting background jobs."""
    def __init__(self, temp_base_dir: Path):
        self.temp_base_dir = temp_base_dir
        self.temp_base_dir.mkdir(parents=True, exist_ok=True)
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()

    def create_job(self, job_id: str, original_filename: str, duration: float, segment_minutes: float, output_format: str) -> Dict[str, Any]:
        job_dir = self.temp_base_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        output_dir = job_dir / "segments"
        output_dir.mkdir(parents=True, exist_ok=True)

        job_data = {
            "job_id": job_id,
            "status": "pending",
            "progress": 0,
            "current_step": "Job initialized",
            "original_filename": original_filename,
            "duration": duration,
            "duration_formatted": format_duration(duration),
            "segment_minutes": segment_minutes,
            "output_format": output_format,
            "job_dir": str(job_dir),
            "output_dir": str(output_dir),
            "segments": [],
            "zip_filename": None,
            "zip_size_formatted": None,
            "error": None,
            "created_at": time.time(),
            "updated_at": time.time()
        }
        with self.lock:
            self.jobs[job_id] = job_data
        return job_data

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return None
            return dict(job)

    def update_job(self, job_id: str, **kwargs):
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id].update(kwargs)
                self.jobs[job_id]["updated_at"] = time.time()

    def delete_job(self, job_id: str) -> bool:
        with self.lock:
            job = self.jobs.pop(job_id, None)
        if job:
            job_dir = Path(job.get("job_dir", ""))
            if job_dir.exists():
                shutil.rmtree(job_dir, ignore_errors=True)
            return True
        return False

    def cleanup_old_jobs(self, max_age_seconds: int = 7200):
        """Remove jobs older than max_age_seconds (default 2 hours)."""
        now = time.time()
        expired_ids = []
        with self.lock:
            for jid, jdata in self.jobs.items():
                if now - jdata.get("created_at", now) > max_age_seconds:
                    expired_ids.append(jid)

        for jid in expired_ids:
            self.delete_job(jid)

    def process_split_job(self, job_id: str, input_file_path: Path):
        """Worker function that runs FFmpeg to split audio into segments."""
        try:
            job = self.get_job(job_id)
            if not job:
                return

            self.update_job(job_id, status="processing", progress=5, current_step="Analyzing audio stream...")

            total_duration = job["duration"]
            seg_len_secs = job["segment_minutes"] * 60.0
            out_fmt = job["output_format"].lower()

            if out_fmt not in OUTPUT_FORMAT_SETTINGS:
                out_fmt = "mp3"

            fmt_cfg = OUTPUT_FORMAT_SETTINGS[out_fmt]
            ext = fmt_cfg["ext"]
            # Resolve input file path if relative
            if not input_file_path.exists():
                project_root = Path(__file__).resolve().parent.parent
                alt_path = project_root / input_file_path
                if alt_path.exists():
                    input_file_path = alt_path
                else:
                    raise FileNotFoundError(f"Input file not found: {input_file_path}")
            # Use stream copy when input format matches desired output format to avoid re‑encoding
            # Additionally, if the input audio codec already matches the target codec, we can also copy.
            codec_name_map = {
                "mp3": "mp3",
                "wav": "pcm_s16le",
                "m4a": "aac",
                "aac": "aac",
                "flac": "flac",
                "ogg": "libvorbis",
                "opus": "libopus",
                "wma": "wmav2",
                "aiff": "pcm_s16be",
            }
            input_ext = input_file_path.suffix.lower()
            # Probe input file for its audio codec
            try:
                probe_info = probe_media(input_file_path)
                input_codec = probe_info.get("audio_codec")
            except Exception:
                input_codec = None
            target_codec = codec_name_map.get(out_fmt)
            if input_ext == ext or (input_codec and target_codec and input_codec.lower() in target_codec.lower()):
                codec_args = ["-c:a", "copy"]
            else:
                codec_args = fmt_cfg["codec_args"]

            # Calculate segments: never discard the final shorter segment
            segments_plan = []
            curr_start = 0.0
            idx = 1
            while curr_start < total_duration:
                remaining = total_duration - curr_start
                curr_len = min(seg_len_secs, remaining)
                if curr_len <= 0.05:
                    break
                segments_plan.append({
                    "index": idx,
                    "start": curr_start,
                    "length": curr_len
                })
                curr_start += curr_len
                idx += 1

            total_segments = len(segments_plan)
            if total_segments == 0:
                raise ValueError("Calculated zero segments from duration.")

            output_dir = Path(job["output_dir"])
            generated_segments = []

            for i, seg in enumerate(segments_plan, start=1):
                seg_idx = seg["index"]
                seg_start = seg["start"]
                seg_len = seg["length"]

                seg_filename = f"Audio_Part_{seg_idx:02d}{ext}"
                seg_path = output_dir / seg_filename

                percent = 5 + int((i - 1) / total_segments * 85)
                step_text = f"Generating segment {i} of {total_segments} ({format_duration(seg_len)})..."
                self.update_job(job_id, progress=percent, current_step=step_text)

                # FFmpeg execution: fast seek -ss before -i, duration -t, strip video -vn
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-ss", f"{seg_start:.3f}",
                    "-i", str(input_file_path),
                    "-t", f"{seg_len:.3f}",
                    "-vn",
                ] + codec_args + [str(seg_path)]

                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode != 0:
                    err_msg = res.stderr[-500:] if res.stderr else "FFmpeg segmentation failed."
                    raise RuntimeError(f"FFmpeg error on segment {i}: {err_msg}")

                if not seg_path.exists() or seg_path.stat().st_size == 0:
                    raise RuntimeError(f"Segment file {seg_filename} was not generated properly.")

                file_size = seg_path.stat().st_size
                generated_segments.append({
                    "index": seg_idx,
                    "filename": seg_filename,
                    "duration": seg_len,
                    "duration_formatted": format_duration(seg_len),
                    "size_bytes": file_size,
                    "size_formatted": format_filesize(file_size),
                    "download_url": f"/api/audio/jobs/{job_id}/download/{seg_filename}"
                })

            # Create ZIP archive containing all segments
            self.update_job(job_id, progress=92, current_step="Packaging all segments into ZIP archive...")
            zip_filename = "AudioSplit_All_Segments.zip"
            zip_path = Path(job["job_dir"]) / zip_filename

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for seg_info in generated_segments:
                    file_to_pack = output_dir / seg_info["filename"]
                    zf.write(file_to_pack, arcname=seg_info["filename"])

            zip_size = zip_path.stat().st_size

            # Mark completed!
            self.update_job(
                job_id,
                status="completed",
                progress=100,
                current_step=f"Successfully generated {total_segments} audio segments!",
                segments=generated_segments,
                zip_filename=zip_filename,
                zip_size_bytes=zip_size,
                zip_size_formatted=format_filesize(zip_size),
                zip_download_url=f"/api/audio/jobs/{job_id}/download-zip"
            )

        except Exception as e:
            self.update_job(
                job_id,
                status="failed",
                progress=0,
                current_step="Processing failed",
                error=str(e)
            )
