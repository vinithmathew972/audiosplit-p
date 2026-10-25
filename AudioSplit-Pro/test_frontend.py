from pathlib import Path

html_path = Path(r"AudioSplit-Pro\frontend\index.html")
css_path = Path(r"AudioSplit-Pro\frontend\style.css")
js_path = Path(r"AudioSplit-Pro\frontend\script.js")
headphone_path = Path(r"AudioSplit-Pro\frontend\assets\headphone.png")

print("=== 1. CHECKING FRONTEND FILE EXISTENCE ===")
assert html_path.exists(), "index.html missing"
assert css_path.exists(), "style.css missing"
assert js_path.exists(), "script.js missing"
assert headphone_path.exists(), "headphone.png missing"
print(f"headphone.png size: {headphone_path.stat().st_size} bytes")

print("\n=== 2. VERIFYING HTML STRUCTURE & REQUIRED UI ELEMENTS ===")
html_text = html_path.read_text(encoding="utf-8")

# Required dashboard texts
assert 'Welcome <span class="gradient-text">Mrs. Julie</span>' in html_text
assert "To our Audio Splitter App" in html_text
assert "Effortlessly split your audio files into smaller segments" in html_text
assert "Good things take a little time. Make it count!" in html_text
assert "SMALLER SEGMENTS" in html_text and "BIGGER POSSIBILITIES" in html_text
assert "assets/headphone.png" in html_text

# Required 4 sidebar navigation items
assert 'data-page="dashboard"' in html_text
assert 'data-page="splitter"' in html_text
assert 'data-page="formats"' in html_text
assert 'data-page="how-it-works"' in html_text

# Audio Splitter page requirements
assert 'id="page-splitter"' in html_text
assert "Split Your Audio" in html_text
assert 'id="dropzone"' in html_text
assert 'data-minutes="5"' in html_text
assert 'data-minutes="10"' in html_text
assert 'data-minutes="15"' in html_text
assert 'data-minutes="20"' in html_text
assert 'data-minutes="30"' in html_text
assert 'data-minutes="custom"' in html_text
assert 'id="downloadZipBtn"' in html_text
assert 'id="startSplitBtn"' in html_text

# Formats page requirements
assert 'id="page-formats"' in html_text
assert "Audio Formats" in html_text
assert "Video Containers" in html_text

# How it works page requirements
assert 'id="page-how-it-works"' in html_text
assert "Upload Media File" in html_text
assert "Choose Segment Duration" in html_text

print("[PASS] All required visual and UI elements verified in index.html.")

print("\n=== 3. VERIFYING CSS COLOR PALETTE & VISUAL SPECIFICATION ===")
css_text = css_path.read_text(encoding="utf-8")
for color in ["#050B1E", "#091638", "#2563FF", "#00CFFF", "#8B5CF6", "#00F5D4", "#F8FAFF", "#A8B9E8"]:
    assert color.lower() in css_text.lower(), f"Required color {color} missing in style.css"
print("[PASS] All exact color palette values found in style.css.")

print("\n=== 4. VERIFYING JAVASCRIPT LOGIC ===")
js_text = js_path.read_text(encoding="utf-8")
assert "initParticles" in js_text
assert "initDashboardEqualizer" in js_text
assert "navigateTo" in js_text
assert "handleFileSelection" in js_text
assert "updateSegmentCalculation" in js_text
assert "initiateSplitJob" in js_text
assert "startJobPolling" in js_text
assert "renderJobResults" in js_text
print("[PASS] All JavaScript workflow functions verified.")

print("\n=============================================")
print("ALL FRONTEND STRUCTURE & STYLE CHECKS PASSED!")
print("=============================================")
