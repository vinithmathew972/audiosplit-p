# AudioSplit Pro
> **Split Audio. Save Time.**

AudioSplit Pro is a high-fidelity, sample-accurate web application designed for fast, effortless audio segmentation. Powered by **FastAPI** and **FFmpeg**, it features a dark neon-blue interface inspired by premium audio hardware and cinematic music visualizations.

---

## Key Features

- **Dark Neon-Blue Aesthetic**: Faithful reproduction of the cinematic AudioSplit Pro dashboard featuring deep indigo gradients, floating musical notes, 3D glowing headphones, and dancing neon audio equalizers.
- **Dedicated 4-Page Navigation**:
  1. **Dashboard**: Cinematic welcome screen with glowing visuals, motivational tagline, and instant launch button.
  2. **Audio Splitter**: Drag-and-drop workspace with honest upload progress, FFprobe technical metadata inspection, preset/custom duration selection, real-time segment breakdown calculation, honest progress polling, and inline audio preview players.
  3. **Formats**: Comprehensive compatibility matrix for 9 common audio formats and 5 video containers, plus live FFmpeg engine capability diagnostics.
  4. **How It Works**: Interactive 4-step workflow guide with best practice tips for long recordings.
- **Universal Media Ingestion**:
  - **Audio Formats**: MP3, WAV, M4A, AAC, FLAC, OGG, WMA, AIFF, OPUS.
  - **Video Containers**: MP4, MOV, MKV, AVI, WEBM, MPEG, MPG (soundtracks extracted with pristine fidelity before splitting).
- **Flexible Splitting Options**:
  - Presets: **5 min, 10 min, 15 min, 20 min, 30 min**.
  - **Custom Duration**: Enter any positive duration in minutes (e.g. 7.5 mins).
  - **Preserves Final Shorter Segment**: Guaranteed never to discard the remainder.
- **Production-Grade Downloads**:
  - Individual segment downloads (e.g. `Audio_Part_01.mp3`, `Audio_Part_02.mp3`).
  - One-click **"Download All as ZIP"** archive packaging all parts.
  - HTML5 inline audio preview players for each segment.
- **Large File Support & Security**:
  - Chunked streaming upload to prevent memory spikes on 1-hour or 2-hour recordings.
  - Subprocess execution with `shell=False` to prevent injection attacks.
  - Path traversal protection on all download endpoints.
  - Automatic background cleanup of temporary job files.

---

## Technology Stack

- **Frontend**: HTML5, Modern CSS3 (Gradients, Glassmorphism, Keyframe animations, SVG ribbons, HTML5 Canvas particles), Vanilla JavaScript (ES6+).
- **Backend**: Python 3.10+, FastAPI, Uvicorn, Python `zipfile`.
- **Media Engine**: FFmpeg 9.0+, FFprobe.

---

## Project Structure

```
AudioSplit-Pro/
│
├── frontend/
│   ├── index.html          # Cinematic multi-page dashboard & splitter UI
│   ├── style.css           # Dark neon-blue theme, animations & responsive grid
│   ├── script.js           # Navigation, FFprobe inspection, polling & players
│   └── assets/
│       └── headphone.png   # 3D glowing headphone illustration asset
│
├── backend/
│   ├── main.py             # FastAPI REST API, endpoints & static mount
│   ├── audio_processor.py  # FFmpeg/FFprobe wrapper, JobManager & ZIP creator
│   ├── requirements.txt    # Python dependencies
│   └── temp/               # Temporary workspace for segmented audio
│
├── README.md               # Complete documentation
└── .gitignore              # Ignored caches, temp files & virtualenvs
```

---

## Installation & Setup (Windows)

### Prerequisites
1. **Python 3.10+**: Verify with:
   ```powershell
   python --version
   ```
2. **FFmpeg & FFprobe**: Ensure `ffmpeg` and `ffprobe` are installed and added to your System `PATH`:
   ```powershell
   ffmpeg -version
   ffprobe -version
   ```

### 1. Install Backend Dependencies
Open PowerShell and navigate to the backend directory:
```powershell
cd d:\audio_split_p\AudioSplit-Pro\backend
pip install -r requirements.txt
```

### 2. Start the FastAPI Server
Run Uvicorn to serve both the backend API and frontend:
```powershell
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Open the Application
Open your web browser and navigate to:
```
http://127.0.0.1:8000
```
*(Alternatively, you can open `frontend/index.html` directly in any modern browser; it will communicate with `http://127.0.0.1:8000` via CORS).*

---

## API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health status and FFmpeg readiness check |
| `GET` | `/api/ffmpeg/info` | Installed FFmpeg version and codec detection |
| `POST` | `/api/audio/analyze` | Upload and analyze media metadata with FFprobe |
| `POST` | `/api/audio/split` | Dispatch background splitting job with duration & format |
| `GET` | `/api/audio/jobs/{job_id}` | Poll job status, progress percentage & step text |
| `GET` | `/api/audio/jobs/{job_id}/download/{filename}` | Download individual audio segment |
| `GET` | `/api/audio/jobs/{job_id}/download-zip` | Download all segments as a ZIP archive |
| `DELETE` | `/api/audio/jobs/{job_id}` | Cancel job and remove temporary files |

---

## Large File & 1-2 Hour Recording Support

- **Memory Efficiency**: Files are streamed to disk in 1MB chunks instead of buffering gigabytes of media into RAM.
- **Asynchronous Segmentation**: FFmpeg processes each cut in the background, updating progress for each segment generated.
- **Resource Retention & Cleanup**: Temporary directories for processed jobs are automatically purged after 2 hours or immediately upon job deletion.
- **Hosting Recommendations**: For cloud deployment, allocate at least 2GB of RAM and temporary NVMe storage proportionate to concurrent users (approx. 500MB storage per active job).
