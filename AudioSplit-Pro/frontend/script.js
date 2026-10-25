/**
 * AudioSplit Pro - Core Frontend Logic
 * Supports Navigation, FFprobe Analysis, Preset/Custom Splitting, Real-time Job Polling, and Downloads
 */

// API Base URL - works seamlessly whether frontend is served from FastAPI or opened standalone
const API_BASE = window.location.origin.includes('5500') || window.location.protocol === 'file:' 
  ? 'http://127.0.0.1:8000' 
  : window.location.origin;

// State management
let currentFile = null;
let analyzedData = null;
let currentDurationMinutes = 10;
let currentOutputFormat = 'mp3';
let activeJobId = null;
let pollingInterval = null;

// ==========================================================================
// 1. INITIALIZATION & AMBIENT VISUALS
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
  initParticles();
  initDashboardEqualizer();
  initNavigation();
  initSplitterControls();
  fetchSystemInfo();
});

/* Ambient Particle Canvas */
function initParticles() {
  const canvas = document.getElementById('particles-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let width, height;
  let particles = [];

  function resize() {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
  }
  window.addEventListener('resize', resize);
  resize();

  const particleCount = Math.min(50, Math.floor(window.innerWidth / 25));
  for (let i = 0; i < particleCount; i++) {
    particles.push({
      x: Math.random() * width,
      y: Math.random() * height,
      radius: Math.random() * 2 + 0.6,
      vx: (Math.random() - 0.5) * 0.4,
      vy: -Math.random() * 0.6 - 0.2,
      color: Math.random() > 0.4 ? 'rgba(0, 207, 255, ' : 'rgba(139, 92, 246, ',
      alpha: Math.random() * 0.6 + 0.2,
      fadeSpeed: Math.random() * 0.008 + 0.003
    });
  }

  function render() {
    ctx.clearRect(0, 0, width, height);
    for (let p of particles) {
      p.x += p.vx;
      p.y += p.vy;
      p.alpha += p.fadeSpeed;
      if (p.alpha > 0.8 || p.alpha < 0.15) {
        p.fadeSpeed = -p.fadeSpeed;
      }
      if (p.y < -10) {
        p.y = height + 10;
        p.x = Math.random() * width;
      }
      if (p.x < -10) p.x = width + 10;
      if (p.x > width + 10) p.x = -10;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      ctx.fillStyle = p.color + Math.max(0, p.alpha) + ')';
      ctx.shadowBlur = 8;
      ctx.shadowColor = '#00CFFF';
      ctx.fill();
    }
    requestAnimationFrame(render);
  }
  render();
}

/* Dashboard Bottom Neon Equalizer Generator */
function initDashboardEqualizer() {
  const container = document.getElementById('dashboardEqBars');
  if (!container) return;
  container.innerHTML = '';
  const totalBars = 36;

  for (let i = 0; i < totalBars; i++) {
    const bar = document.createElement('div');
    bar.className = 'eq-bar';
    const minH = 8 + Math.floor(Math.sin(i / totalBars * Math.PI) * 15);
    const maxH = 25 + Math.floor(Math.sin(i / totalBars * Math.PI) * 35);
    const duration = (0.7 + Math.random() * 0.9).toFixed(2);
    const delay = (Math.random() * 0.8).toFixed(2);

    bar.style.animation = `eqDancing ${duration}s ease-in-out infinite alternate`;
    bar.style.animationDelay = `${delay}s`;
    bar.style.setProperty('--min-h', `${minH}px`);
    bar.style.setProperty('--max-h', `${maxH}px`);
    container.appendChild(bar);
  }
}

// ==========================================================================
// 2. NAVIGATION & MOBILE DRAWER
// ==========================================================================

function initNavigation() {
  const navButtons = document.querySelectorAll('.nav-item');
  navButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetPage = btn.getAttribute('data-page');
      navigateTo(targetPage);
    });
  });

  const mobileBtn = document.getElementById('mobileMenuBtn');
  const sidebar = document.getElementById('sidebar');
  if (mobileBtn && sidebar) {
    mobileBtn.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });
  }
}

function navigateTo(pageId) {
  // Update sidebar active button
  document.querySelectorAll('.nav-item').forEach(btn => {
    if (btn.getAttribute('data-page') === pageId) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  // Switch page visibility
  document.querySelectorAll('.page-content').forEach(p => {
    p.classList.remove('active');
  });

  const target = document.getElementById(`page-${pageId}`);
  if (target) {
    target.classList.add('active');
  }

  // Reset scroll position to top immediately on all potential scroll containers
  const mainViewport = document.querySelector('.main-viewport');
  if (mainViewport) {
    mainViewport.scrollTop = 0;
  }
  if (target) {
    target.scrollTop = 0;
  }
  window.scrollTo(0, 0);
  document.documentElement.scrollTop = 0;
  document.body.scrollTop = 0;

  // Close mobile sidebar if open
  const sidebar = document.getElementById('sidebar');
  if (sidebar && sidebar.classList.contains('open')) {
    sidebar.classList.remove('open');
  }
}

// ==========================================================================
// 3. AUDIO SPLITTER WORKFLOW
// ==========================================================================

function initSplitterControls() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('mediaFileInput');

  if (dropzone && fileInput) {
    // Drag & drop events
    ['dragenter', 'dragover'].forEach(name => {
      dropzone.addEventListener(name, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach(name => {
      dropzone.addEventListener(name, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('dragover');
      });
    });

    dropzone.addEventListener('drop', (e) => {
      if (e.dataTransfer && e.dataTransfer.files.length > 0) {
        handleFileSelection(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleFileSelection(e.target.files[0]);
      }
    });
  }

  // Duration pill clicks
  const durationPills = document.querySelectorAll('.duration-pill');
  const customBox = document.getElementById('customDurationBox');
  const customInput = document.getElementById('customMinutesInput');

  durationPills.forEach(pill => {
    pill.addEventListener('click', () => {
      durationPills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      const val = pill.getAttribute('data-minutes');

      if (val === 'custom') {
        customBox.style.display = 'block';
        if (customInput.value && parseFloat(customInput.value) > 0) {
          currentDurationMinutes = parseFloat(customInput.value);
        } else {
          customInput.value = '7.5';
          currentDurationMinutes = 7.5;
        }
      } else {
        customBox.style.display = 'none';
        currentDurationMinutes = parseFloat(val);
      }
      updateSegmentCalculation();
    });
  });

  if (customInput) {
    customInput.addEventListener('input', () => {
      const val = parseFloat(customInput.value);
      if (val && val > 0) {
        currentDurationMinutes = val;
        updateSegmentCalculation();
      }
    });
  }

  // Format selection cards
  const formatCards = document.querySelectorAll('.format-option-card');
  formatCards.forEach(card => {
    card.addEventListener('click', () => {
      formatCards.forEach(c => c.classList.remove('active'));
      card.classList.add('active');
      const radio = card.querySelector('input[type="radio"]');
      if (radio) {
        radio.checked = true;
        currentOutputFormat = radio.value;
      }
    });
  });

  // Start split button
  const startBtn = document.getElementById('startSplitBtn');
  if (startBtn) {
    startBtn.addEventListener('click', initiateSplitJob);
  }
}

/* Analyze file on upload */
function handleFileSelection(file) {
  if (!file) return;
  currentFile = file;

  hideError();
  const progressWrapper = document.getElementById('uploadProgressWrapper');
  const progressBar = document.getElementById('uploadProgressBar');
  const statusText = document.getElementById('uploadStatusText');
  const percentText = document.getElementById('uploadPercentText');

  progressWrapper.style.display = 'block';
  statusText.textContent = `Uploading & analyzing "${file.name}"...`;
  progressBar.style.width = '0%';
  percentText.textContent = '0%';

  const formData = new FormData();
  formData.append('file', file);

  const xhr = new XMLHttpRequest();
  xhr.open('POST', `${API_BASE}/api/audio/analyze`, true);

  xhr.upload.onprogress = (e) => {
    if (e.lengthComputable) {
      const percent = Math.round((e.loaded / e.total) * 90);
      progressBar.style.width = `${percent}%`;
      percentText.textContent = `${percent}%`;
    }
  };

  xhr.onload = () => {
    progressBar.style.width = '100%';
    percentText.textContent = '100%';

    if (xhr.status === 200) {
      try {
        const resp = JSON.parse(xhr.responseText);
        analyzedData = resp;
        displayAnalyzedMetadata(resp);
      } catch (err) {
        showError('Invalid response from media analyzer.');
        progressWrapper.style.display = 'none';
      }
    } else {
      let errMsg = 'Failed to analyze media file.';
      try {
        const errJson = JSON.parse(xhr.responseText);
        if (errJson.detail) errMsg = errJson.detail;
      } catch (e) {}
      showError(errMsg);
      progressWrapper.style.display = 'none';
    }
  };

  xhr.onerror = () => {
    showError('Network error connecting to AudioSplit backend.');
    progressWrapper.style.display = 'none';
  };

  xhr.send(formData);
}

function displayAnalyzedMetadata(data) {
  document.getElementById('metaFileName').textContent = data.filename || currentFile.name;
  document.getElementById('metaDuration').textContent = data.duration_formatted || '-';
  document.getElementById('metaFileSize').textContent = data.size_formatted || '-';
  
  let codecLabel = data.audio_codec.toUpperCase();
  if (data.is_video) {
    codecLabel += ' (Extracted from Video)';
  }
  document.getElementById('metaAudioCodec').textContent = codecLabel;

  // Show config panel and hide upload card
  document.getElementById('uploadCard').style.display = 'none';
  document.getElementById('configCard').style.display = 'block';

  updateSegmentCalculation();
}

/* Calculate segment count and detail breakdown */
function updateSegmentCalculation() {
  if (!analyzedData || !analyzedData.duration) return;

  const totalSecs = analyzedData.duration;
  const segSecs = currentDurationMinutes * 60.0;

  if (segSecs <= 0) return;

  let count = Math.floor(totalSecs / segSecs);
  const remainder = totalSecs % segSecs;
  let hasRemainder = remainder > 0.05;
  let totalSegments = count + (hasRemainder ? 1 : 0);

  const resultTextElem = document.getElementById('calcResultText');
  if (totalSegments <= 1 && !hasRemainder) {
    resultTextElem.innerHTML = `1 segment of <strong>${formatDurationText(totalSecs)}</strong> (File duration is within chosen split interval).`;
  } else if (!hasRemainder) {
    resultTextElem.innerHTML = `<strong>${totalSegments} equal segments</strong> of <strong>${currentDurationMinutes} minutes</strong> each.`;
  } else {
    const fullSegText = count > 0 ? `<strong>${count} segment${count > 1 ? 's' : ''}</strong> of ${currentDurationMinutes} min` : '';
    const remText = `<strong>1 final segment</strong> of ${formatDurationText(remainder)}`;
    resultTextElem.innerHTML = `<strong>${totalSegments} segments total:</strong> ${fullSegText ? fullSegText + ' + ' : ''}${remText}.`;
  }
}

function formatDurationText(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  if (mins >= 60) {
    const hrs = Math.floor(mins / 60);
    const remMins = mins % 60;
    return `${hrs}h ${remMins}m ${secs}s`;
  }
  return `${mins}m ${secs}s`;
}

/* Initiate background audio splitting job */
function initiateSplitJob() {
  if (!analyzedData) {
    showError('Please upload and inspect a valid audio or video file first.');
    return;
  }
  if (currentDurationMinutes <= 0) {
    showError('Please enter a positive segment duration.');
    return;
  }

  hideError();
  document.getElementById('configCard').style.display = 'none';
  document.getElementById('processingCard').style.display = 'block';
  document.getElementById('resultsCard').style.display = 'none';

  // Set initial honest progress
  updateProcessingProgress(5, 'Submitting split task to FFmpeg engine...');

  const formData = new FormData();
  if (analyzedData.file_token) {
    formData.append('file_token', analyzedData.file_token);
  } else if (currentFile) {
    formData.append('file', currentFile);
  }
  formData.append('duration_minutes', currentDurationMinutes);
  formData.append('output_format', currentOutputFormat);

  fetch(`${API_BASE}/api/audio/split`, {
    method: 'POST',
    body: formData
  })
    .then(async res => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Failed to start split job.' }));
        throw new Error(err.detail || 'Failed to start split job.');
      }
      return res.json();
    })
    .then(data => {
      activeJobId = data.job_id;
      startJobPolling(activeJobId);
    })
    .catch(err => {
      showError(err.message);
      document.getElementById('processingCard').style.display = 'none';
      document.getElementById('configCard').style.display = 'block';
    });
}

/* Honest status polling */
function startJobPolling(jobId) {
  if (pollingInterval) clearInterval(pollingInterval);

  pollingInterval = setInterval(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/audio/jobs/${jobId}`);
      if (!res.ok) throw new Error('Failed to retrieve job status.');

      const job = await res.json();
      updateProcessingProgress(job.progress, job.current_step);

      if (job.status === 'completed') {
        clearInterval(pollingInterval);
        pollingInterval = null;
        renderJobResults(job);
      } else if (job.status === 'failed') {
        clearInterval(pollingInterval);
        pollingInterval = null;
        showError(`Processing error: ${job.error || 'Audio segmentation failed.'}`);
        document.getElementById('processingCard').style.display = 'none';
        document.getElementById('configCard').style.display = 'block';
      }
    } catch (e) {
      // Continue polling unless permanent error
    }
  }, 750);
}

function updateProcessingProgress(percent, stepText) {
  const bar = document.getElementById('jobProgressBar');
  const percentText = document.getElementById('jobProgressPercent');
  const stepElem = document.getElementById('processingStepText');

  const safePercent = Math.min(100, Math.max(0, percent || 0));
  if (bar) bar.style.width = `${safePercent}%`;
  if (percentText) percentText.textContent = `${safePercent}%`;
  if (stepElem && stepText) stepElem.textContent = stepText;
}

/* Render completed segments and download links */
function renderJobResults(job) {
  document.getElementById('processingCard').style.display = 'none';
  const resultsCard = document.getElementById('resultsCard');
  resultsCard.style.display = 'block';

  const countHeadline = document.getElementById('resultsCountHeadline');
  countHeadline.textContent = `Successfully Created ${job.segments.length} Audio Segment${job.segments.length > 1 ? 's' : ''}!`;

  const zipBtn = document.getElementById('downloadZipBtn');
  zipBtn.href = `${API_BASE}${job.zip_download_url}`;
  document.getElementById('zipSizeDisplay').textContent = job.zip_size_formatted || 'ZIP';

  const listContainer = document.getElementById('segmentsListContainer');
  listContainer.innerHTML = '';

  job.segments.forEach(seg => {
    const card = document.createElement('div');
    card.className = 'segment-row-card';

    const segNum = String(seg.index).padStart(2, '0');
    const dlUrl = `${API_BASE}${seg.download_url}`;

    card.innerHTML = `
      <div class="segment-left">
        <span class="segment-badge">Part #${segNum}</span>
        <div class="segment-details">
          <span class="segment-filename">${seg.filename}</span>
          <div class="segment-meta">
            <span>Duration: ${seg.duration_formatted}</span> &bull; 
            <span>Size: ${seg.size_formatted}</span>
          </div>
        </div>
      </div>
      <div class="segment-audio-player">
        <audio controls preload="none" src="${dlUrl}"></audio>
      </div>
      <div class="segment-right">
        <a href="${dlUrl}" download="${seg.filename}" class="btn btn-outline" style="padding: 0.5rem 1rem; font-size: 0.85rem;">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:15px;height:15px;">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          Download
        </a>
      </div>
    `;
    listContainer.appendChild(card);
  });
}

/* Reset splitter to start over */
function resetSplitter() {
  if (pollingInterval) clearInterval(pollingInterval);
  pollingInterval = null;

  if (activeJobId) {
    fetch(`${API_BASE}/api/audio/jobs/${activeJobId}`, { method: 'DELETE' }).catch(() => {});
  }

  currentFile = null;
  analyzedData = null;
  activeJobId = null;

  const fileInput = document.getElementById('mediaFileInput');
  if (fileInput) fileInput.value = '';

  document.getElementById('uploadProgressWrapper').style.display = 'none';
  document.getElementById('uploadCard').style.display = 'block';
  document.getElementById('configCard').style.display = 'none';
  document.getElementById('processingCard').style.display = 'none';
  document.getElementById('resultsCard').style.display = 'none';
  hideError();
}

// ==========================================================================
// 4. FORMATS & DIAGNOSTICS
// ==========================================================================

async function fetchSystemInfo() {
  try {
    const res = await fetch(`${API_BASE}/api/ffmpeg/info`);
    if (!res.ok) return;
    const data = await res.json();

    const vElem = document.getElementById('ffmpegVersionText');
    if (vElem && data.version) {
      vElem.textContent = data.version;
    }

    const cElem = document.getElementById('ffmpegCodecsText');
    if (cElem && data.encoders) {
      const available = Object.keys(data.encoders).filter(k => data.encoders[k]);
      cElem.textContent = available.join(', ');
    }
  } catch (err) {
    const vElem = document.getElementById('ffmpegVersionText');
    if (vElem) vElem.textContent = 'FFmpeg engine online (via FastAPI backend)';
  }
}

// ==========================================================================
// 5. ERROR HANDLING UTILS
// ==========================================================================

function showError(msg) {
  const banner = document.getElementById('errorBanner');
  const text = document.getElementById('errorMessageText');
  if (banner && text) {
    text.textContent = msg;
    banner.style.display = 'flex';
  }
}

function hideError() {
  const banner = document.getElementById('errorBanner');
  if (banner) banner.style.display = 'none';
}
