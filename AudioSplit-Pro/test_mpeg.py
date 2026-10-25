import sys
import zipfile
from pathlib import Path

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_dir))

from audio_processor import (
    probe_media,
    JobManager,
    SUPPORTED_AUDIO_EXTENSIONS,
    SUPPORTED_VIDEO_EXTENSIONS,
    ALL_SUPPORTED_EXTENSIONS
)

def test_mpeg_support():
    print("=== 1. VERIFYING EXTENSION REGISTRY ===")
    required_formats = [
        "aac", "aif", "aiff", "avi", "flac", "m4a", "mkv", "mov", 
        "mp3", "mp4", "ogg", "opus", "wav", "webm", "wma", "mpeg", "mpg"
    ]
    for fmt in required_formats:
        ext = f".{fmt}"
        assert ext in ALL_SUPPORTED_EXTENSIONS, f"Missing extension in ALL_SUPPORTED_EXTENSIONS: {ext}"
    print(f"[PASS] All {len(required_formats)} required extensions registered: {sorted(list(ALL_SUPPORTED_EXTENSIONS))}")

    print("\n=== 2. TESTING .MPEG ANALYSIS WITH FFPROBE ===")
    mpeg_path = Path("test_sample.mpeg")
    assert mpeg_path.exists(), "test_sample.mpeg missing"
    mpeg_info = probe_media(mpeg_path)
    print(f"File: {mpeg_info['filename']} | Duration: {mpeg_info['duration_formatted']} ({mpeg_info['duration']}s)")
    print(f"Container: {mpeg_info['format_name']} | Audio Codec: {mpeg_info['audio_codec']} | Video detected: {mpeg_info['is_video']}")
    assert abs(mpeg_info["duration"] - 30.0) < 1.0
    assert mpeg_info["is_video"] is True
    assert mpeg_info["audio_codec"] == "mp2"
    print("[PASS] .MPEG file analyzed successfully with FFprobe.")

    print("\n=== 3. TESTING .MPG ANALYSIS WITH FFPROBE ===")
    mpg_path = Path("test_sample.mpg")
    assert mpg_path.exists(), "test_sample.mpg missing"
    mpg_info = probe_media(mpg_path)
    print(f"File: {mpg_info['filename']} | Duration: {mpg_info['duration_formatted']} ({mpg_info['duration']}s)")
    print(f"Container: {mpg_info['format_name']} | Audio Codec: {mpg_info['audio_codec']} | Video detected: {mpg_info['is_video']}")
    assert abs(mpg_info["duration"] - 25.0) < 1.0
    assert mpg_info["is_video"] is True
    assert mpg_info["audio_codec"] == "mp2"
    print("[PASS] .MPG file analyzed successfully with FFprobe.")

    print("\n=== 4. TESTING REJECTION OF FILE WITHOUT AUDIO STREAM ===")
    no_audio_path = Path("test_no_audio.mpeg")
    assert no_audio_path.exists(), "test_no_audio.mpeg missing"
    try:
        probe_media(no_audio_path)
        print("[FAIL] File with no audio should have been rejected!")
        sys.exit(1)
    except ValueError as e:
        print("[PASS] Clean error triggered as expected:", str(e))
        assert "does not contain an audio track" in str(e)

    print("\n=== 5. TESTING AUDIO EXTRACTION & SPLITTING FROM .MPEG ===")
    temp_dir = backend_dir / "temp"
    jm = JobManager(temp_dir)
    job_mpeg = jm.create_job("job_mpeg_test", "test_sample.mpeg", 30.0, 0.25, "mp3") # 15s segments
    jm.process_split_job("job_mpeg_test", mpeg_path)
    job_res = jm.get_job("job_mpeg_test")
    assert job_res["status"] == "completed"
    assert len(job_res["segments"]) == 2
    for s in job_res["segments"]:
        print(f"  Part #{s['index']:02d}: {s['filename']} ({s['duration_formatted']}, {s['size_formatted']})")
    print("[PASS] .MPEG soundtrack extracted and split into 2 parts.")

    print("\n=== 6. TESTING AUDIO EXTRACTION & SPLITTING FROM .MPG (PRESERVING FINAL SEGMENT) ===")
    # 25s file split into 10s (0.166667 min) -> 10s + 10s + 5s (3 segments)
    job_mpg = jm.create_job("job_mpg_test", "test_sample.mpg", 25.0, 0.166667, "mp3")
    jm.process_split_job("job_mpg_test", mpg_path)
    mpg_res = jm.get_job("job_mpg_test")
    assert mpg_res["status"] == "completed"
    assert len(mpg_res["segments"]) == 3
    final_seg = mpg_res["segments"][2]
    assert abs(final_seg["duration"] - 5.0) < 1.0, f"Final segment expected 5s, got {final_seg['duration']}s"
    print(f"Final segment preserved: {final_seg['filename']} ({final_seg['duration_formatted']})")

    # Check ZIP archive
    zip_path = Path(mpg_res["job_dir"]) / mpg_res["zip_filename"]
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path, "r") as zf:
        contents = zf.namelist()
        print("ZIP archive contents:", contents)
        assert len(contents) == 3
    print("[PASS] .MPG soundtrack extracted, split into 3 parts, and bundled in ZIP.")

    # Cleanup
    jm.delete_job("job_mpeg_test")
    jm.delete_job("job_mpg_test")
    print("\n=======================================================")
    print("ALL .MPEG & .MPG FUNCTIONAL & AUDIO TESTS PASSED!")
    print("=======================================================")

if __name__ == "__main__":
    test_mpeg_support()
