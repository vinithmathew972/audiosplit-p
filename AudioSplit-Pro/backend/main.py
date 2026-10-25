import os
import re
import uuid
import shutil
import asyncio
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from audio_processor import (
    probe_media,
    get_ffmpeg_capabilities,
    JobManager,
    ALL_SUPPORTED_EXTENSIONS,
    OUTPUT_FORMAT_SETTINGS
)

BASE_DIR = Path(__file__).resolve().parent
TEMP_DIR = BASE_DIR / "temp"
FRONTEND_DIR = BASE_DIR.parent / "frontend"

app = FastAPI(
    title="AudioSplit Pro API",
    description="Professional Audio Splitting Web API powered by FastAPI and FFmpeg",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

job_manager = JobManager(TEMP_DIR)

def sanitize_filename(filename: str) -> str:
    """Strip dangerous characters and keep safe filename characters."""
    base = Path(filename).name
    clean = re.sub(r'[^a-zA-Z0-9_.-]', '_', base)
    if not clean or clean.startswith('.'):
        clean = f"audio_{uuid.uuid4().hex[:8]}" + Path(filename).suffix
    return clean

# Response Models
class HealthResponse(BaseModel):
    status: str
    ffmpeg_ready: bool
    version: str

@app.get("/api/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint to verify backend and FFmpeg readiness."""
    caps = get_ffmpeg_capabilities()
    is_ready = not caps["version"].startswith("FFmpeg check error")
    return HealthResponse(
        status="ok",
        ffmpeg_ready=is_ready,
        version=caps["version"]
    )

@app.get("/api/ffmpeg/info")
def ffmpeg_info():
    """Returns detected FFmpeg version and codec support."""
    return get_ffmpeg_capabilities()

@app.post("/api/audio/analyze")
async def analyze_audio(file: UploadFile = File(...)):
    """Analyze uploaded media file using ffprobe and return duration & technical metadata."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALL_SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{ext}'. Supported formats: {', '.join(sorted(ALL_SUPPORTED_EXTENSIONS))}"
        )

    # Save to a temporary analysis directory
    analysis_id = str(uuid.uuid4())
    analysis_dir = TEMP_DIR / "analysis" / analysis_id
    analysis_dir.mkdir(parents=True, exist_ok=True)

    safe_name = sanitize_filename(file.filename or "media_input" + ext)
    file_path = analysis_dir / safe_name

    try:
        # Stream file to disk to avoid excessive memory usage
        with open(file_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                f.write(chunk)

        metadata = probe_media(file_path)
        metadata["file_token"] = analysis_id
        metadata["stored_filename"] = safe_name
        metadata["filename"] = file.filename or safe_name
        return JSONResponse(status_code=status.HTTP_200_OK, content=metadata)

    except ValueError as ve:
        shutil.rmtree(analysis_dir, ignore_errors=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        shutil.rmtree(analysis_dir, ignore_errors=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analysis failed: {str(e)}")

@app.post("/api/audio/split")
async def split_audio(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    file_token: Optional[str] = Form(None),
    duration_minutes: float = Form(...),
    output_format: str = Form("mp3")
):
    """
    Start splitting audio file. Accepts either an uploaded file or an analyzed file_token.
    Processes in the background and returns job_id for polling.
    """
    if duration_minutes <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duration must be a positive number greater than 0."
        )

    out_fmt = output_format.lower().strip()
    if out_fmt not in OUTPUT_FORMAT_SETTINGS:
        out_fmt = "mp3"

    job_id = str(uuid.uuid4())
    job_dir = TEMP_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    input_file_path = None
    original_filename = "audio_input"

    # Case 1: Pre-analyzed file token
    if file_token:
        analysis_dir = TEMP_DIR / "analysis" / file_token
        if analysis_dir.exists():
            candidates = list(analysis_dir.glob("*"))
            if candidates:
                cand = candidates[0]
                original_filename = cand.name
                input_file_path = job_dir / cand.name
                shutil.copy2(cand, input_file_path)
                # Cleanup analysis dir
                shutil.rmtree(analysis_dir, ignore_errors=True)

    # Case 2: Direct file upload
    if not input_file_path and file:
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALL_SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format '{ext}'. Supported: {', '.join(sorted(ALL_SUPPORTED_EXTENSIONS))}"
            )
        original_filename = sanitize_filename(file.filename or f"media{ext}")
        input_file_path = job_dir / original_filename
        with open(input_file_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)

    if not input_file_path or not input_file_path.exists():
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid media file provided for splitting."
        )

    # Probe input media to verify duration and audio track
    try:
        media_info = probe_media(input_file_path)
        total_duration = media_info["duration"]
    except Exception as e:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid media file: {str(e)}"
        )

    # Initialize job in manager
    job_data = job_manager.create_job(
        job_id=job_id,
        original_filename=original_filename,
        duration=total_duration,
        segment_minutes=duration_minutes,
        output_format=out_fmt
    )

    # Schedule background processing
    background_tasks.add_task(job_manager.process_split_job, job_id, input_file_path)
    # Schedule cleanup of old jobs
    background_tasks.add_task(job_manager.cleanup_old_jobs)

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "job_id": job_id,
            "status": "pending",
            "message": "Split job queued successfully.",
            "duration": total_duration,
            "segment_minutes": duration_minutes,
            "output_format": out_fmt
        }
    )

@app.get("/api/audio/jobs/{job_id}")
def get_job_status(job_id: str):
    """Poll job status, progress percentage, and generated segments."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return JSONResponse(status_code=status.HTTP_200_OK, content=job)

@app.get("/api/audio/jobs/{job_id}/download/{filename}")
def download_segment(job_id: str, filename: str):
    """Download an individual generated audio segment."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    # Prevent path traversal
    safe_name = Path(filename).name
    file_path = Path(job["output_dir"]) / safe_name

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment file not found.")

    ext = file_path.suffix.lstrip(".").lower()
    mime = OUTPUT_FORMAT_SETTINGS.get(ext, {}).get("mime", "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        filename=safe_name,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'}
    )

@app.get("/api/audio/jobs/{job_id}/download-zip")
def download_zip(job_id: str):
    """Download all split segments packaged in a single ZIP archive."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    zip_filename = job.get("zip_filename") or "AudioSplit_All_Segments.zip"
    zip_path = Path(job["job_dir"]) / zip_filename

    if not zip_path.exists() or not zip_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ZIP archive not found or not ready yet.")

    return FileResponse(
        path=str(zip_path),
        filename=zip_filename,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'}
    )

@app.delete("/api/audio/jobs/{job_id}")
def delete_job(job_id: str):
    """Cancel job and delete temporary files."""
    success = job_manager.delete_job(job_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return {"status": "deleted", "job_id": job_id}

# Mount static frontend directory for single-origin serving
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
