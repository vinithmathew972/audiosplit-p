import sys
from pathlib import Path

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_dir))

from audio_processor import (
    probe_media,
    get_ffmpeg_capabilities,
    JobManager,
    OUTPUT_FORMAT_SETTINGS,
    format_duration
)
import zipfile

def run_all_tests():
    print("=== 1. VERIFYING FFMPEG AND FFPROBE CAPABILITIES ===")
    caps = get_ffmpeg_capabilities()
    print("FFmpeg version:", caps["version"])
    print("Supported audio encoders:", caps["encoders"])
    assert caps["encoders"].get("libmp3lame") is True
    assert caps["encoders"].get("pcm_s16le") is True
    print("[PASS] FFmpeg and FFprobe verified.")

    print("\n=== 2. TESTING MEDIA ANALYSIS (MP3) ===")
    mp3_info = probe_media(Path("test_sample.mp3"))
    print(f"MP3: {mp3_info['filename']} | Duration: {mp3_info['duration_formatted']} ({mp3_info['duration']}s)")
    print(f"Codec: {mp3_info['audio_codec']} | Channels: {mp3_info['channels']} | Rate: {mp3_info['sample_rate']}")
    assert abs(mp3_info["duration"] - 75.0) < 1.0
    assert mp3_info["is_video"] is False
    print("[PASS] MP3 analysis verified.")

    print("\n=== 3. TESTING MEDIA ANALYSIS (MP4 VIDEO EXTRACT) ===")
    mp4_info = probe_media(Path("test_sample.mp4"))
    print(f"MP4: {mp4_info['filename']} | Duration: {mp4_info['duration_formatted']} ({mp4_info['duration']}s)")
    print(f"Video container detected: {mp4_info['is_video']} | Audio Codec: {mp4_info['audio_codec']}")
    assert mp4_info["is_video"] is True
    assert abs(mp4_info["duration"] - 45.0) < 1.0
    print("[PASS] Video container analysis verified.")

    print("\n=== 4. TESTING REJECTION OF CORRUPT/INVALID MEDIA ===")
    try:
        probe_media(Path("test_corrupt.mp3"))
        print("[FAIL] Corrupt file was not rejected!")
        sys.exit(1)
    except ValueError as e:
        print("[PASS] Corrupt file properly rejected with error:", str(e))

    print("\n=== 5. TESTING AUDIO SPLITTING & SHORTER FINAL SEGMENT PRESERVATION ===")
    temp_dir = backend_dir / "temp"
    jm = JobManager(temp_dir)
    job = jm.create_job(
        job_id="test_job_001",
        original_filename="test_sample.mp3",
        duration=75.0,
        segment_minutes=0.5, # 30 seconds -> 75s = 30s + 30s + 15s (3 segments)
        output_format="mp3"
    )
    print("Job initialized:", job["job_id"], "| Target segment duration:", job["segment_minutes"], "minutes")

    # Run splitting
    jm.process_split_job("test_job_001", Path("test_sample.mp3"))

    job_res = jm.get_job("test_job_001")
    print("Job status:", job_res["status"], "| Progress:", job_res["progress"], "%")
    num_segs = len(job_res["segments"])
    print("Total segments produced:", num_segs)
    assert job_res["status"] == "completed"
    assert num_segs == 3, f"Expected 3 segments, got {num_segs}"

    for s in job_res["segments"]:
        print(f"  Part #{s['index']:02d}: {s['filename']} - Duration: {s['duration_formatted']} - Size: {s['size_formatted']}")

    # Verify final shorter segment
    seg3 = job_res["segments"][2]
    assert abs(seg3["duration"] - 15.0) < 1.0, f"Segment 3 duration expected ~15s, got {seg3['duration']}"
    print("[PASS] All segments generated and final shorter segment (15s) preserved!")

    print("\n=== 6. TESTING ZIP ARCHIVE CREATION & INTEGRITY ===")
    zip_path = Path(job_res["job_dir"]) / job_res["zip_filename"]
    assert zip_path.exists(), "ZIP archive not created"
    print(f"ZIP Archive: {zip_path.name} ({zip_path.stat().st_size} bytes)")

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        print("ZIP contents:", names)
        assert len(names) == 3
        for s in job_res["segments"]:
            assert s["filename"] in names
    print("[PASS] ZIP archive contains all 3 segments.")

    print("\n=== 7. TESTING VIDEO AUDIO EXTRACTION & SPLITTING ===")
    job_vid = jm.create_job(
        job_id="test_job_vid_002",
        original_filename="test_sample.mp4",
        duration=45.0,
        segment_minutes=0.333333, # 20 seconds -> 45s = 20s + 20s + 5s (3 segments)
        output_format="mp3"
    )
    jm.process_split_job("test_job_vid_002", Path("test_sample.mp4"))
    job_vid_res = jm.get_job("test_job_vid_002")
    print("Video Job status:", job_vid_res["status"], "| Segments:", len(job_vid_res["segments"]))
    assert job_vid_res["status"] == "completed"
    assert len(job_vid_res["segments"]) == 3
    print("[PASS] Video audio extraction and segmentation verified.")

    print("\n=== 8. TESTING OUTPUT FORMATS (WAV, FLAC, M4A) ===")
    for fmt in ["wav", "flac", "m4a"]:
        fmt_jid = f"test_fmt_{fmt}"
        jm.create_job(fmt_jid, "test_sample.mp3", 75.0, 1.0, fmt)
        jm.process_split_job(fmt_jid, Path("test_sample.mp3"))
        f_res = jm.get_job(fmt_jid)
        assert f_res["status"] == "completed"
        out_ext = OUTPUT_FORMAT_SETTINGS[fmt]["ext"]
        assert f_res["segments"][0]["filename"].endswith(out_ext)
        print(f"  Format [{fmt.upper()}]: Generated {len(f_res['segments'])} segments ending in {out_ext}")
        jm.delete_job(fmt_jid)
    print("[PASS] Additional audio output formats verified.")

    print("\n=== 9. TESTING CLEANUP ===")
    jm.delete_job("test_job_001")
    jm.delete_job("test_job_vid_002")
    assert not (temp_dir / "test_job_001").exists()
    assert not (temp_dir / "test_job_vid_002").exists()
    print("[PASS] Temporary files cleaned up.")

    print("\n========================================================")
    print("ALL 9 MEDIA PROCESSING & EXTRACTION TESTS PASSED!")
    print("========================================================")

if __name__ == "__main__":
    run_all_tests()
