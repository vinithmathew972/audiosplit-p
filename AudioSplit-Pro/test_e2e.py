import os
import sys
import time
import zipfile
import io
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health():
    print("\n--- Test 1: Health & FFmpeg Info ---")
    resp = client.get("/api/health")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    data = resp.json()
    print("Health response:", data)
    assert data["status"] == "ok"
    assert data["ffmpeg_ready"] is True

    info_resp = client.get("/api/ffmpeg/info")
    assert info_resp.status_code == 200
    info_data = info_resp.json()
    print("Detected encoders:", info_data["encoders"])
    print("[PASS] Health & FFmpeg capabilities verified.")

def test_analyze_valid_mp3():
    print("\n--- Test 2: Analyze Valid MP3 ---")
    mp3_path = Path("test_sample.mp3")
    assert mp3_path.exists(), "test_sample.mp3 does not exist"

    with open(mp3_path, "rb") as f:
        resp = client.post("/api/audio/analyze", files={"file": ("test_sample.mp3", f, "audio/mpeg")})
    assert resp.status_code == 200, f"Analyze failed: {resp.text}"
    meta = resp.json()
    print(f"MP3 Meta: Duration={meta['duration']}s, Formatted={meta['duration_formatted']}, Codec={meta['audio_codec']}, Size={meta['size_formatted']}")
    assert abs(meta["duration"] - 75.0) < 1.0, f"Unexpected duration: {meta['duration']}"
    assert meta["is_video"] is False
    assert "file_token" in meta
    print("[PASS] MP3 analysis verified.")
    return meta["file_token"]

def test_analyze_video():
    print("\n--- Test 3: Analyze Video (MP4) Audio Extraction Support ---")
    mp4_path = Path("test_sample.mp4")
    assert mp4_path.exists(), "test_sample.mp4 does not exist"

    with open(mp4_path, "rb") as f:
        resp = client.post("/api/audio/analyze", files={"file": ("test_sample.mp4", f, "video/mp4")})
    assert resp.status_code == 200, f"Video analyze failed: {resp.text}"
    meta = resp.json()
    print(f"MP4 Meta: Duration={meta['duration']}s, is_video={meta['is_video']}, AudioCodec={meta['audio_codec']}")
    assert meta["is_video"] is True
    assert abs(meta["duration"] - 45.0) < 1.0
    print("[PASS] Video analysis verified.")

def test_analyze_corrupt_file():
    print("\n--- Test 4: Reject Invalid / Corrupt File ---")
    corrupt_path = Path("test_corrupt.mp3")
    with open(corrupt_path, "rb") as f:
        resp = client.post("/api/audio/analyze", files={"file": ("test_corrupt.mp3", f, "audio/mpeg")})
    print("Corrupt file HTTP status:", resp.status_code, "Detail:", resp.json())
    assert resp.status_code == 400, "Should have rejected corrupt file"
    print("[PASS] Corrupt file rejection verified.")

def test_split_and_downloads(file_token: str):
    print("\n--- Test 5: Audio Split Job, Polling, Downloads, & Shorter Final Segment ---")
    # 75s file split into 0.5 minute (30s) segments -> expects 3 segments (30s, 30s, 15s)
    split_payload = {
        "file_token": file_token,
        "duration_minutes": "0.5",
        "output_format": "mp3"
    }
    resp = client.post("/api/audio/split", data=split_payload)
    assert resp.status_code == 202, f"Split initiation failed: {resp.text}"
    init_data = resp.json()
    job_id = init_data["job_id"]
    print(f"Job queued: id={job_id}")

    # Poll until completed
    max_wait = 20
    start_time = time.time()
    final_job = None
    while time.time() - start_time < max_wait:
        poll_resp = client.get(f"/api/audio/jobs/{job_id}")
        assert poll_resp.status_code == 200
        poll_data = poll_resp.json()
        print(f"Polling job {job_id}: status={poll_data['status']}, progress={poll_data['progress']}%, step='{poll_data['current_step']}'")
        if poll_data["status"] == "completed":
            final_job = poll_data
            break
        elif poll_data["status"] == "failed":
            raise RuntimeError(f"Job failed: {poll_data.get('error')}")
        time.sleep(0.5)

    assert final_job is not None, "Job timed out"
    assert len(final_job["segments"]) == 3, f"Expected 3 segments, got {len(final_job['segments'])}"
    print(f"Segments produced: {len(final_job['segments'])}")
    for seg in final_job["segments"]:
        print(f"  - Part {seg['index']}: {seg['filename']}, Duration={seg['duration_formatted']}, Size={seg['size_formatted']}")

    # Check that final segment duration is around 15s (shorter final segment preserved!)
    assert abs(final_job["segments"][2]["duration"] - 15.0) < 2.0, "Final shorter segment not preserved correctly"

    # Test individual segment download
    seg1 = final_job["segments"][0]
    dl_resp = client.get(f"/api/audio/jobs/{job_id}/download/{seg1['filename']}")
    assert dl_resp.status_code == 200
    assert len(dl_resp.content) > 1000
    print(f"[PASS] Downloaded segment 1 ({len(dl_resp.content)} bytes)")

    # Test ZIP download
    zip_resp = client.get(f"/api/audio/jobs/{job_id}/download-zip")
    assert zip_resp.status_code == 200
    zip_buffer = io.BytesIO(zip_resp.content)
    with zipfile.ZipFile(zip_buffer, "r") as zf:
        namelist = zf.namelist()
        print("ZIP archive contents:", namelist)
        assert len(namelist) == 3
        for seg in final_job["segments"]:
            assert seg["filename"] in namelist
    print("[PASS] ZIP download and integrity verified.")

    # Test Job cleanup
    del_resp = client.delete(f"/api/audio/jobs/{job_id}")
    assert del_resp.status_code == 200
    print("[PASS] Job deletion and cleanup verified.")

def test_frontend_serving():
    print("\n--- Test 6: Static Frontend Serving ---")
    resp = client.get("/")
    assert resp.status_code == 200
    assert "AudioSplit Pro" in resp.text
    assert "Welcome" in resp.text
    print("[PASS] Frontend served at / correctly.")

if __name__ == "__main__":
    test_health()
    token = test_analyze_valid_mp3()
    test_analyze_video()
    test_analyze_corrupt_file()
    test_split_and_downloads(token)
    test_frontend_serving()
    print("\n==========================================")
    print("ALL 6 AUTOMATED END-TO-END TESTS PASSED!")
    print("==========================================")
